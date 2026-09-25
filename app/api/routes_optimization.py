import json
import threading

import logfire
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_admin
from app.db.database import get_db
from app.db.models import Experiment, User, Workspace
from app.services.optimization_lab import DEFAULT_PRESETS, run_experiment
from app.services.retrieval.qdrant_service import (
    apply_quantization,
    get_collection_quantization,
)


router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["optimization"])

# One benchmark at a time per workspace
_running: set[str] = set()
_running_lock = threading.Lock()


def _workspace_or_404(workspace_id: str, db: Session) -> Workspace:
    ws = db.get(Workspace, workspace_id)
    if ws is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")
    return ws


def _latest_experiment(db: Session, workspace_id: str) -> Experiment | None:
    return (
        db.query(Experiment)
        .filter(Experiment.workspace_id == workspace_id)
        .order_by(Experiment.created_at.desc())
        .first()
    )


class OptimizeRequest(BaseModel):
    presets: list[str] = DEFAULT_PRESETS


class ApplyRequest(BaseModel):
    preset: str


@router.post("/optimize")
def start_optimization(
    workspace_id: str,
    request: OptimizeRequest,
    background_tasks: BackgroundTasks,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ws = _workspace_or_404(workspace_id, db)

    if request.presets:
        for p in request.presets:
            try:
                from app.services.retrieval.qdrant_service import build_quantization_config

                build_quantization_config(p)
            except ValueError:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown preset: {p}")

    with _running_lock:
        if ws.id in _running:
            raise HTTPException(status.HTTP_409_CONFLICT, "An experiment is already running for this workspace")
        _running.add(ws.id)

    exp = Experiment(workspace_id=ws.id, status="running")
    db.add(exp)
    db.commit()
    db.refresh(exp)

    background_tasks.add_task(_run_and_release, exp.id, ws.id, request.presets or DEFAULT_PRESETS)
    logfire.info(f"Optimization experiment started for '{ws.name}' by {admin.email}")
    return {"experiment_id": exp.id, "status": "running", "presets": request.presets or DEFAULT_PRESETS}


def _run_and_release(experiment_id: str, workspace_id: str, presets: list[str]) -> None:
    try:
        run_experiment(experiment_id, presets)
    finally:
        with _running_lock:
            _running.discard(workspace_id)


@router.get("/optimize")
def get_optimization_results(
    workspace_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ws = _workspace_or_404(workspace_id, db)
    exp = _latest_experiment(db, ws.id)
    if exp is None:
        return {"status": "never_run", "results": None}
    return {
        "experiment_id": exp.id,
        "status": exp.status,
        "error": exp.error,
        "results": json.loads(exp.results_json) if exp.results_json else None,
        "created_at": exp.created_at.isoformat() if exp.created_at else None,
    }


@router.post("/optimize/apply")
def apply_preset(
    workspace_id: str,
    request: ApplyRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ws = _workspace_or_404(workspace_id, db)
    try:
        apply_quantization(ws.qdrant_collection, request.preset)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown preset: {request.preset}")
    except Exception as e:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            f"Qdrant rejected the preset (server must be 1.18+ for TurboQuant): {str(e)[:200]}",
        )
    return {"applied": request.preset, "collection": ws.qdrant_collection}


@router.get("/quantization")
def current_quantization(
    workspace_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ws = _workspace_or_404(workspace_id, db)
    return {"preset": get_collection_quantization(ws.qdrant_collection)}
