# Self-Adaptive Agentic RAG Platform: LangGraph · Guardrails · LLM Gateway · React

A production-grade, **self-adaptive** Retrieval-Augmented Generation platform. Upload any batch of documents — the platform **analyzes the corpus by itself**, learns the domain (topics, terminology, persona, answer style), generates its own prompts and guardrails, and starts answering questions. No code or config changes per domain.

## 🤖 Multi-agent pipeline (Self-RAG)

Queries run through a **six-agent LangGraph pipeline** with quality loops:

```
planner (intent) → memory condenser (long chats) →
  conversational → responder → done
  retrieval → query rewriter → retriever → document grader ─┐
                ▲            (nothing relevant? retry once) │ ≥1 relevant
                └───────────────────────────────────────────┘
                                          → responder → verifier → done
                                              ▲ (unsupported? regenerate once)
```

- **Query Rewriter** turns follow-ups into standalone search queries ("what about its memory?" → names the actual subject)
- **Document Grader** filters retrieved chunks in one batched call; if nothing is relevant it retries with a broadened query, then forces an honest "not in the knowledge base" answer instead of a hallucination
- **Answer Verifier** checks the draft against the sources and regenerates once if unsupported (the UI shows a ✅ Verified / ⚠️ badge)
- **Memory Condenser** compresses long conversations so prompts stay small and follow-ups stay sharp

## 🌟 How self-adaptation works

1. **Admin creates a knowledge base (workspace)** and uploads documents (PDF · HTML · DOCX · PPTX · TXT).
2. **Ingestion** parses → chunks → embeds (Gemini 3072-dim) → indexes into a per-workspace Qdrant collection.
3. **Corpus Analyzer** (LLM) samples the indexed chunks and produces a **Knowledge Profile**: domain name, summary, topics, terminology, audience, sample questions, off-topic examples, assistant persona and answer style.
4. **Prompts adapt**: the Planner and Responder prompts are built from the profile — no hardcoded domains.
5. **Guardrails adapt**: NeMo rails are auto-generated per workspace from the profile (persona, capabilities, off-topic refusals) on top of always-on jailbreak protection.
6. Upload more documents later and the platform **merges and re-learns** the profile automatically.

Query flow: **Guardrails → Planner (intent) → Rewriter → Retriever (Qdrant + FlashRank) → Grader → Responder (profile persona) → Verifier**, with conversation memory per user + workspace.

## 🏗️ System Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for diagrams.

1. **Frontend**: React 19 + Vite + Tailwind SPA (login/register, chat with reasoning steps + sources, admin dashboard) — served by FastAPI in production
2. **API + Auth**: FastAPI with JWT auth and roles (`admin` manages, `user` chats), SQLite via SQLAlchemy (users / workspaces / documents)
3. **Agentic Core**: LangGraph Planner → Retriever → Responder with MemorySaver
4. **Retrieval**: per-workspace Qdrant Cloud collections + FlashRank local reranker
5. **LLM Gateway**: Portkey (Groq `gpt-oss-120b` primary → `gpt-oss-20b` fallback)
6. **Guardrails**: per-workspace auto-generated NeMo rails
7. **Ingestion**: background pipeline with per-document status tracking
8. **Observability**: Logfire + LangSmith · **Evals**: RAGAS suite (legacy `/query` endpoint kept for the eval pipeline)

## 🚀 Running locally

### One command — `start.sh` / `stop.sh`
```bash
./start.sh              # start in the background (checks deps, builds frontend if stale, health-checks)
./stop.sh               # gracefully stop the background platform
./start.sh --restart    # restart
./start.sh --build      # force a frontend rebuild first
./start.sh --reinstall  # reinstall python deps first
PORT=8010 ./start.sh    # different port
tail -f platform.log    # follow the logs
```
Start logs to `platform.log`, writes the process id to `.platform.pid`, and waits until the API answers before reporting success. `stop.sh` uses the PID file (with a process-name fallback), escalates SIGTERM → SIGKILL, and confirms the port is free.

### Foreground / development mode — `run.sh`
```bash
./run.sh                # run in the foreground (Ctrl+C stops it)
./run.sh --dev          # frontend dev server (:5173, hot reload) + API with --reload
```
The script prefers the `rag/` virtualenv (falls back to `venv/`), auto-installs missing dependencies (using `uv` when available), and refuses to start if port 8000 is occupied. Open http://localhost:8000 — login as the seeded admin (`ADMIN_EMAIL` / `ADMIN_PASSWORD` from `.env`).

### Manual setup (equivalent)
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..   # builds frontend/dist
uvicorn app.main:app --reload --port 8000              # serves API + SPA on :8000
```

### Frontend development mode (hot reload)
```bash
cd frontend && npm run dev   # Vite on :5173, proxies /auth /workspaces /users to :8000
```

### Workflow
1. Log in as admin → **Knowledge Bases** → create one.
2. Drag & drop a batch of documents on one topic → watch per-file status (`queued → processing → indexed`), then the workspace turns `analyzing` → `ready` once the profile is learned.
3. Inspect the **learned profile** (domain, topics, terminology, sample questions).
4. Go to **Chat**, pick the knowledge base, and ask questions.
5. Manage users under **Users** (promote to admin / delete).

## 🔑 Environment variables

Core keys: `GEMINI_API_KEY`, `QDRANT_CLUSTER_ENDPOINT`, `QDRANT_API_KEY`, `PORTKEY_API_KEY`, `GROQ_API_KEY`, `GROQ_SLUG`, `PORTKEY_CONFIG`.
Platform keys: `JWT_SECRET`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `DB_PATH`, `UPLOADS_DIR`, `FRONTEND_ORIGIN`. See `DOCS/05_ENVIRONMENT_VARIABLES.md`.

> **Note on models**: Groq retired the old Llama chat models; the gateway now uses `openai/gpt-oss-120b` (primary) and `openai/gpt-oss-20b` (fallback). The saved Portkey dashboard config may still reference the retired models — the app currently routes around it, so update the dashboard config to the new model names when you can.

## 📂 Project Structure

```
RAGproject/
├── app/                        # Core Python package
│   ├── agents/                 # LangGraph nodes + profile-driven prompt builders
│   ├── api/                    # Routers: chat, workspaces, documents, users
│   ├── auth/                   # JWT security, dependencies, register/login
│   ├── db/                     # SQLAlchemy models + session (platform.db)
│   ├── gateway/                # Portkey client, manual fallback routing
│   ├── guardrails/             # Per-workspace auto-generated NeMo rails
│   ├── ingestion/              # Loaders, chunker, background pipeline
│   ├── services/               # Qdrant, embeddings, corpus analyzer
│   ├── config.py               # Configuration
│   └── main.py                 # FastAPI entry point + SPA serving
├── frontend/                   # React 19 + Vite + Tailwind SPA
│   └── src/
│       ├── pages/Chat.jsx      # Chat with reasoning steps + sources
│       └── pages/admin/        # Knowledge bases, upload, profile, users
├── evals/                      # RAGAS eval pipeline + golden dataset
├── scripts/e2e_verify.py       # End-to-end platform verification script
├── DATA/                       # Sample corpora (true_data / noisy_data)
├── DOCS/                       # Component deep-dives
└── Dockerfile                  # Multi-stage: node build → uvicorn serves SPA
```

## ✅ Key Features

- **Self-adaptive**: learns domain, persona, topics and guardrails from uploaded documents — works for any domain out of the box.
- **Multi-workspace**: isolated knowledge bases with dedicated Qdrant collections and profiles.
- **Multi-user with roles**: JWT auth; admins manage documents/knowledge bases/users, users chat.
- **Live ingestion status**: per-document `queued → processing → indexed/failed` with polling UI.
- **Agentic query planning**, **two-stage retrieval** (vector + FlashRank), **conversation memory** per user + workspace.
- **Auto-generated NeMo guardrails** per workspace + always-on jailbreak protection.
- **Resilient LLM calls**: primary→fallback routing with rate-limit backoff.
- **Observability**: Logfire + LangSmith tracing.
- **Evals**: RAGAS metrics and the golden dataset still run against the legacy `/query` endpoint.

## 🐳 Docker

```bash
docker build -t adaptive-rag .
docker run -p 8080:8080 --env-file .env adaptive-rag
```
The multi-stage build compiles the React frontend and serves it from the same uvicorn process.
