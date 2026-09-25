from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.db.database import get_db
from app.db.models import Document, QueryLog, User, Workspace


router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("")
def platform_stats(admin=Depends(require_admin), db: Session = Depends(get_db)):
    """Aggregated platform numbers for the admin Overview tab."""
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_workspaces = db.query(func.count(Workspace.id)).scalar() or 0
    total_documents = db.query(func.count(Document.id)).scalar() or 0
    total_chunks = db.query(func.coalesce(func.sum(Document.num_chunks), 0)).scalar() or 0

    day_ago = datetime.now(timezone.utc) - timedelta(days=1)
    queries_24h = (
        db.query(func.count(QueryLog.id)).filter(QueryLog.created_at >= day_ago).scalar() or 0
    )
    total_queries = db.query(func.count(QueryLog.id)).scalar() or 0

    verified_row = (
        db.query(func.count(QueryLog.id)).filter(QueryLog.verified.is_(True)).scalar() or 0
    )
    verified_pct = round(100 * verified_row / total_queries, 1) if total_queries else 100.0

    avg_latency = db.query(func.avg(QueryLog.latency_ms)).scalar()

    recent = (
        db.query(
            QueryLog.question,
            QueryLog.user_email,
            QueryLog.status,
            QueryLog.verified,
            QueryLog.latency_ms,
            QueryLog.created_at,
            Workspace.name.label("workspace_name"),
        )
        .join(Workspace, QueryLog.workspace_id == Workspace.id, isouter=True)
        .order_by(QueryLog.created_at.desc())
        .limit(12)
        .all()
    )

    workspace_breakdown = (
        db.query(
            Workspace.name,
            func.count(QueryLog.id).label("queries"),
        )
        .join(QueryLog, QueryLog.workspace_id == Workspace.id, isouter=True)
        .group_by(Workspace.name)
        .order_by(func.count(QueryLog.id).desc())
        .limit(6)
        .all()
    )

    return {
        "totals": {
            "users": total_users,
            "workspaces": total_workspaces,
            "documents": total_documents,
            "chunks": total_chunks,
            "queries": total_queries,
            "queries_24h": queries_24h,
        },
        "verified_pct": verified_pct,
        "avg_latency_ms": round(avg_latency) if avg_latency is not None else None,
        "recent_queries": [
            {
                "question": r.question[:110],
                "user": r.user_email,
                "workspace": r.workspace_name or "—",
                "status": r.status,
                "verified": r.verified,
                "latency_ms": r.latency_ms,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in recent
        ],
        "workspace_activity": [
            {"workspace": r.name, "queries": r.queries or 0} for r in workspace_breakdown
        ],
    }
