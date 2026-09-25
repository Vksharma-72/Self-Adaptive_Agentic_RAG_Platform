import json
import os
import shutil

import logfire
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_admin
from app.db.database import get_db
from app.db.models import Document, User, Workspace
from app.services.retrieval.qdrant_service import drop_collection
from app.config import settings


router = APIRouter(prefix="/workspaces", tags=["workspaces"])


class WorkspaceCreate(BaseModel):
    name: str
    description: str = ""


class WorkspaceOut(BaseModel):
    id: str
    name: str
    description: str
    status: str
    profile_json: str | None
    created_at: str

    class Config:
        from_attributes = True


def _workspace_or_404(workspace_id: str, db: Session) -> Workspace:
    ws = db.get(Workspace, workspace_id)
    if ws is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")
    return ws


@router.post("", status_code=201)
def create_workspace(
    request: WorkspaceCreate,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if not request.name.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Workspace name is required")

    existing = db.query(Workspace).filter(Workspace.name == request.name.strip()).first()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "A workspace with this name already exists")

    ws = Workspace(
        name=request.name.strip(),
        description=request.description.strip(),
        qdrant_collection="",  # set below once the id exists
        created_by=user.id,
    )
    db.add(ws)
    db.flush()
    ws.qdrant_collection = f"ws_{ws.id}"
    db.commit()
    db.refresh(ws)
    logfire.info(f"Workspace created: '{ws.name}' ({ws.id}) by {user.email}")
    return _out(ws)


@router.get("")
def list_workspaces(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workspaces = db.query(Workspace).order_by(Workspace.created_at).all()
    return [_out(ws) for ws in workspaces]


@router.get("/{workspace_id}")
def get_workspace(
    workspace_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _out(_workspace_or_404(workspace_id, db))


@router.get("/{workspace_id}/profile")
def get_profile(
    workspace_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ws = _workspace_or_404(workspace_id, db)
    if not ws.profile_json:
        return {"workspace_id": ws.id, "status": ws.status, "profile": None}
    return {
        "workspace_id": ws.id,
        "status": ws.status,
        "profile": json.loads(ws.profile_json),
    }


@router.post("/{workspace_id}/reanalyze", status_code=202)
def reanalyze_workspace(
    workspace_id: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Re-runs the corpus analyzer without uploading anything (admin action)."""
    ws = _workspace_or_404(workspace_id, db)
    if ws.status in ("ingesting", "analyzing"):
        raise HTTPException(status.HTTP_409_CONFLICT, "Workspace is already processing")

    ws.status = "analyzing"
    db.commit()

    from app.services.corpus_analyzer import analyze_workspace

    background_tasks.add_task(analyze_workspace, ws.id)
    logfire.info(f"Manual re-analysis triggered for '{ws.name}' by {user.email}")
    return {"workspace_id": ws.id, "status": "analyzing"}


@router.delete("/{workspace_id}", status_code=204)
def delete_workspace(
    workspace_id: str,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ws = _workspace_or_404(workspace_id, db)

    drop_collection(ws.qdrant_collection)
    db.query(Document).filter(Document.workspace_id == ws.id).delete()

    shutil.rmtree(os.path.join(settings.UPLOADS_DIR, ws.id), ignore_errors=True)

    logfire.info(f"Workspace deleted: '{ws.name}' ({ws.id}) by {user.email}")
    db.delete(ws)
    db.commit()


def _out(ws: Workspace) -> dict:
    return {
        "id": ws.id,
        "name": ws.name,
        "description": ws.description,
        "status": ws.status,
        "profile_json": ws.profile_json,
        "created_at": ws.created_at.isoformat() if ws.created_at else None,
    }
