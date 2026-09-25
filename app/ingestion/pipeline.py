import threading
import uuid

import logfire
from qdrant_client.http import models

from app.db.database import SessionLocal
from app.db.models import Document, Workspace
from app.ingestion.chunking.splitter import chunk_text
from app.ingestion.loaders.loader_html import parse_html
from app.ingestion.loaders.office import parse_office
from app.ingestion.loaders.pdf import parse_pdf
from app.ingestion.loaders.text import parse_text
from app.services.retrieval.embeddings import embed_texts
from app.services.retrieval.qdrant_service import ensure_collection

SUPPORTED_EXTENSIONS = {"pdf", "html", "htm", "txt", "docx", "pptx"}

# One lock per workspace so concurrent upload batches don't interleave
# ingestion + profile analysis for the same collection
_workspace_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _lock_for(workspace_id: str) -> threading.Lock:
    with _locks_guard:
        if workspace_id not in _workspace_locks:
            _workspace_locks[workspace_id] = threading.Lock()
        return _workspace_locks[workspace_id]


def extract_text(file_path: str, filename: str) -> str:
    ext = filename.lower().rsplit(".", 1)[-1]
    if ext == "pdf":
        return parse_pdf(file_path)
    if ext in ("html", "htm"):
        return parse_html(file_path)
    if ext == "txt":
        return parse_text(file_path)
    if ext in ("docx", "pptx"):
        return parse_office(file_path)
    return ""


def process_document(doc_id: str) -> bool:
    """Parse -> chunk -> embed -> index one document. Updates its DB status.

    Opens its own DB session (runs in a background thread).
    """
    db = SessionLocal()
    try:
        doc = db.get(Document, doc_id)
        if doc is None:
            logfire.warning(f"Document {doc_id} vanished before processing.")
            return False

        ws = db.get(Workspace, doc.workspace_id)
        doc.status = "processing"
        db.commit()

        with logfire.span("Processing Document", file=doc.filename):
            text = extract_text(doc.stored_path, doc.filename)
            if not text or not text.strip():
                doc.status = "failed"
                doc.error = "No text could be extracted from this file."
                db.commit()
                logfire.warning(f"No text extracted from {doc.filename}.")
                return False

            chunks = chunk_text(text)
            if not chunks:
                doc.status = "failed"
                doc.error = "Chunking produced no usable chunks."
                db.commit()
                return False

            ensure_collection(ws.qdrant_collection)

            with logfire.span("Vectorizing & Indexing"):
                embeddings = embed_texts(chunks)
                points = [
                    models.PointStruct(
                        id=str(uuid.uuid4()),
                        vector=vector,
                        payload={
                            "text": chunk,
                            "source": doc.filename,
                            "source_type": doc.filename.lower().rsplit(".", 1)[-1],
                            "workspace_id": doc.workspace_id,
                            "document_id": doc.id,
                        },
                    )
                    for chunk, vector in zip(chunks, embeddings)
                ]
                from app.services.retrieval.qdrant_service import client as qdrant_client

                qdrant_client.upsert(collection_name=ws.qdrant_collection, points=points)

            doc.status = "indexed"
            doc.num_chunks = len(points)
            doc.error = None
            db.commit()
            logfire.info(f"Indexed {len(points)} chunks from {doc.filename}.")
            return True

    except Exception as e:
        logfire.error(f"Failed to process document {doc_id}: {e}")
        try:
            doc = db.get(Document, doc_id)
            if doc:
                doc.status = "failed"
                doc.error = str(e)[:1000]
                db.commit()
        except Exception:
            pass
        return False
    finally:
        db.close()


def process_batch(workspace_id: str, doc_ids: list[str]) -> None:
    """Background task: index a batch of documents, then re-learn the profile."""
    with _lock_for(workspace_id):
        db = SessionLocal()
        try:
            ws = db.get(Workspace, workspace_id)
            if ws is None:
                return
            ws.status = "ingesting"
            db.commit()
        finally:
            db.close()

        any_indexed = False
        for doc_id in doc_ids:
            if process_document(doc_id):
                any_indexed = True

        if not any_indexed:
            db = SessionLocal()
            try:
                ws = db.get(Workspace, workspace_id)
                if ws and ws.status == "ingesting":
                    ws.status = "empty" if not ws.profile_json else "ready"
                    db.commit()
            finally:
                db.close()
            return

        # Corpus changed — the platform re-learns its knowledge profile
        db = SessionLocal()
        try:
            ws = db.get(Workspace, workspace_id)
            if ws:
                ws.status = "analyzing"
                db.commit()
        finally:
            db.close()

        from app.services.corpus_analyzer import analyze_workspace

        analyze_workspace(workspace_id)
