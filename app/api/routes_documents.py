import os

import logfire
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_admin
from app.config import settings
from app.db.database import get_db
from app.db.models import Document, User, Workspace
from app.ingestion.pipeline import SUPPORTED_EXTENSIONS, process_batch
from app.services.retrieval.qdrant_service import delete_document_points


router = APIRouter(prefix="/workspaces/{workspace_id}/documents", tags=["documents"])


def _workspace_or_404(workspace_id: str, db: Session) -> Workspace:
    ws = db.get(Workspace, workspace_id)
    if ws is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")
    return ws


def _out(doc: Document) -> dict:
    return {
        "id": doc.id,
        "filename": doc.filename,
        "status": doc.status,
        "num_chunks": doc.num_chunks,
        "error": doc.error,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
    }


@router.post("", status_code=201)
def upload_documents(
    workspace_id: str,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin uploads one or more files; they are queued and processed in the background."""
    ws = _workspace_or_404(workspace_id, db)

    ws_dir = os.path.join(settings.UPLOADS_DIR, ws.id)
    os.makedirs(ws_dir, exist_ok=True)

    created = []
    rejected = []
    for file in files:
        filename = os.path.basename(file.filename or "unnamed")
        ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
        if ext not in SUPPORTED_EXTENSIONS:
            rejected.append({"filename": filename, "reason": f".{ext} is not supported"})
            continue

        doc = Document(workspace_id=ws.id, filename=filename, stored_path="")
        db.add(doc)
        db.flush()
        # Prefix with the doc id so same-named uploads never overwrite each other
        stored_path = os.path.join(ws_dir, f"{doc.id}_{filename}")
        doc.stored_path = stored_path
        db.commit()
        db.refresh(doc)

        with open(stored_path, "wb") as f:
            f.write(file.file.read())

        created.append(doc)
        logfire.info(f"Document queued: {filename} -> workspace '{ws.name}'")

    if created:
        ws.status = "ingesting"
        db.commit()
        background_tasks.add_task(process_batch, ws.id, [d.id for d in created])

    return {
        "queued": [_out(d) for d in created],
        "rejected": rejected,
    }


@router.get("")
def list_documents(
    workspace_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ws = _workspace_or_404(workspace_id, db)
    docs = (
        db.query(Document)
        .filter(Document.workspace_id == ws.id)
        .order_by(Document.created_at)
        .all()
    )
    return [_out(d) for d in docs]


@router.delete("/{document_id}", status_code=204)
def delete_document(
    workspace_id: str,
    document_id: str,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ws = _workspace_or_404(workspace_id, db)
    doc = db.get(Document, document_id)
    if doc is None or doc.workspace_id != ws.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")

    delete_document_points(ws.qdrant_collection, doc.id)
    try:
        os.remove(doc.stored_path)
    except OSError:
        pass

    db.delete(doc)
    db.commit()
    logfire.info(f"Document deleted: {doc.filename} from workspace '{ws.name}'")
