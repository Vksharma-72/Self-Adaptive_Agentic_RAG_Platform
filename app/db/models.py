import uuid
from datetime import datetime, timezone

from sqlalchemy import String, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    # "admin" can manage workspaces/documents/users; "user" can only chat
    role: Mapped[str] = mapped_column(String(16), default="user")
    created_at: Mapped[datetime] = mapped_column(default=_now)


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    # Dedicated Qdrant collection, e.g. "ws_<id>" — one per workspace
    qdrant_collection: Mapped[str] = mapped_column(String(255))
    # JSON-serialized KnowledgeProfile produced by the corpus analyzer
    profile_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    # "empty" -> "ingesting" -> "analyzing" -> "ready" | "failed"
    status: Mapped[str] = mapped_column(String(32), default="empty")
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(default=_now)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id"), index=True
    )
    filename: Mapped[str] = mapped_column(String(512))
    stored_path: Mapped[str] = mapped_column(String(1024))
    # "queued" -> "processing" -> "indexed" | "failed"
    status: Mapped[str] = mapped_column(String(32), default="queued")
    num_chunks: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_now)


class Experiment(Base):
    """One Optimization Lab run (TurboQuant / scalar quantization benchmark)."""

    __tablename__ = "experiments"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id"), index=True
    )
    # "running" -> "done" | "failed"
    status: Mapped[str] = mapped_column(String(32), default="running")
    # JSON: {"bench": {"vectors": n, "queries": n}, "results": [{"preset", "recall_at_5",
    # "latency_p50_ms", "latency_p95_ms", "memory_saved_pct", "status", "note"}...]}
    results_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_now)


class QueryLog(Base):
    """One chat query against a workspace — powers the Overview dashboard."""

    __tablename__ = "query_logs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id"), index=True
    )
    user_email: Mapped[str] = mapped_column(String(255))
    question: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(64))
    verified: Mapped[bool] = mapped_column(default=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=_now)
