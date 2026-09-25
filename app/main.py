# ============================================================
# CRITICAL: logfire MUST be configured before ALL other imports
# so that spans from all modules are captured from the start.
# ============================================================
import logfire
import os
from dotenv import load_dotenv

load_dotenv()
logfire.configure(token=os.getenv("LOGFIRE_TOKEN"))

# Now safe to import app modules - logfire is already active
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.routes_chat import router as chat_router
from app.api.routes_documents import router as documents_router
from app.api.routes_optimization import router as optimization_router
from app.api.routes_stats import router as stats_router
from app.api.routes_users import router as users_router
from app.api.routes_workspaces import router as workspaces_router
from app.auth.routes import router as auth_router, seed_admin
from app.config import settings
from app.db.database import init_db


# Initialize FastAPI
app = FastAPI(title="Self-Adaptive Agentic RAG Platform")


@app.on_event("startup")
def startup_event():
    init_db()
    seed_admin()


# CORS: the React dev server runs on FRONTEND_ORIGIN (Vite default :5173).
# In production the built SPA is served by FastAPI itself, so CORS is moot there.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- API routers ---
app.include_router(auth_router)
app.include_router(workspaces_router)
app.include_router(documents_router)
app.include_router(users_router)
app.include_router(optimization_router)
app.include_router(stats_router)
app.include_router(chat_router)


@app.get("/")
def home():
    return {"message": "Self-Adaptive Agentic RAG Platform API is live."}


@app.get("/graph")
def get_graph_image():
    """
    Returns the Mermaid image of the agent's workflow.
    """
    try:
        png_bytes = rag_agent_png()
        return Response(content=png_bytes, media_type="image/png")
    except Exception as e:
        return {"error": f"Could not generate graph image: {e}"}


def rag_agent_png() -> bytes:
    from app.agents.graph import rag_agent

    return rag_agent.get_graph().draw_mermaid_png()


# --- Production SPA serving (built React frontend) ---
# `npm run build` outputs to frontend/dist; FastAPI serves it so a single
# uvicorn process deploys the whole platform.
FRONTEND_DIST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")

if os.path.isdir(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        """Serves built static files, falling back to index.html for client-side routes."""
        candidate = os.path.join(FRONTEND_DIST, full_path)
        if full_path and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
