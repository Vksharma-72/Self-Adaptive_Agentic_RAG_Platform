import time

import logfire
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.agents.graph import rag_agent
from app.auth.dependencies import get_current_user
from app.config import settings
from app.db.database import get_db
from app.db.models import QueryLog, User, Workspace
from app.guardrails import guard_for_workspace


router = APIRouter(tags=["chat"])


class QueryRequest(BaseModel):
    q: str
    thread_id: Optional[str] = "default_user"


def _run_rag(
    q: str,
    thread_id: str,
    workspace: Workspace | None,
    current_user_email: str = "api",
) -> dict:
    """Shared RAG execution for the authenticated and legacy endpoints."""
    initial_state = {
        "messages": [{"role": "user", "content": q}],
        "current_query": q,
        "intent": "retrieval",
        "search_query": q,
        "documents": [],
        "graded_documents": [],
        "plan": ["Start"],
        "status": "Initializing Graph...",
        "retrieval_attempts": 0,
        "answer_revision": 0,
        "verified": False,
        "regenerate": False,
        "condensed_history": "",
        "workspace_id": workspace.id if workspace else None,
        "collection": workspace.qdrant_collection if workspace else settings.QDRANT_COLLECTION,
        "profile": _parse_profile(workspace),
    }

    config = {"configurable": {"thread_id": thread_id}}

    try:
        # Gate 1: generated NeMo Guardrails — blocks off-topic, jailbreaks, small talk
        rail_fired, rail_response = guard_for_workspace(
            q,
            workspace.id if workspace else "legacy",
            workspace.profile_json if workspace else None,
        )
        if rail_fired:
            logfire.info(f"🛡️ Request blocked by guardrails | user={current_user_email} thread={thread_id}")
            return {
                "question": q,
                "answer": rail_response,
                "thought_process": ["Intent: Guardrails Fired", "Retrieval: Skipped"],
                "status": "Blocked by guardrails.",
                "sources": [],
                "verified": True,
            }

        # Gate 2: multi-agent LangGraph pipeline (planner → rewriter → grader → responder → verifier)
        final_output = rag_agent.invoke(initial_state, config=config)

        return {
            "question": q,
            "answer": final_output.get("final_answer"),
            "thought_process": final_output.get("plan"),
            "status": final_output.get("status"),
            "sources": final_output.get("graded_documents") or final_output.get("documents", []),
            "verified": final_output.get("verified", True),
        }
    except Exception as e:
        logfire.error(f"❌ Backend Execution Failed: {e}")
        return {
            "question": q,
            "answer": "I apologize, but I encountered an internal error while processing your request. Please try again later.",
            "thought_process": ["Error encountered during execution."],
            "status": "error",
            "sources": [],
            "verified": False,
        }


def _parse_profile(workspace: Workspace | None) -> dict | None:
    import json

    if not workspace or not workspace.profile_json:
        return None
    try:
        return json.loads(workspace.profile_json)
    except (TypeError, json.JSONDecodeError):
        return None


@router.post("/workspaces/{workspace_id}/query")
def workspace_query(
    workspace_id: str,
    request: QueryRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Chat against a workspace's learned knowledge base. Any logged-in user."""
    workspace = db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")

    # Namespace conversation memory per user+workspace so histories never cross
    thread_id = f"{workspace_id}:{user.id}:{request.thread_id}"

    started = time.perf_counter()
    result = _run_rag(request.q, thread_id, workspace, current_user_email=user.email)
    latency_ms = int((time.perf_counter() - started) * 1000)

    # Activity log for the admin Overview dashboard
    try:
        db.add(QueryLog(
            workspace_id=workspace_id,
            user_email=user.email,
            question=request.q[:1000],
            status=(result.get("status") or "unknown")[:64],
            verified=bool(result.get("verified", False)),
            latency_ms=latency_ms,
        ))
        db.commit()
    except Exception as e:
        logfire.warning(f"Query log write failed: {e}")

    return result


@router.post("/query")
def legacy_query(request: QueryRequest):
    """Legacy unauthenticated endpoint — used by the evals pipeline.

    Searches the original single 'enterprise_rag' collection with no profile.
    """
    return _run_rag(request.q, request.thread_id or "default_user", None)
