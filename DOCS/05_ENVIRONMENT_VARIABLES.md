# 🔑 Environment Variables & Configuration

The project uses a `.env` file for local development. All configuration is managed via **Pydantic Settings** in `app/config.py` for strict type safety. Copy `.env.example` to `.env` and fill in your values before running anything.

---

## 🧠 LLMs

| Variable | Description | Example |
| :--- | :--- | :--- |
| `GROQ_API_KEY` | Primary key for Groq LLM calls (Planner + Responder nodes) | `gsk_...` |
| `GROQ_FALLBACK_API_KEY` | Second Groq key used by Portkey as the fallback target; can be the same as primary | `gsk_...` |

---

## 🔀 LLM Gateway

| Variable | Description | Example |
| :--- | :--- | :--- |
| `PORTKEY_API_KEY` | API key for Portkey — enables routing, fallback, caching, and observability across all LLM calls | `pk-...` |

---

## 🌐 Gemini Embeddings

| Variable | Description | Example |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | Google Gemini API key used to generate 3072-dim embeddings via `gemini-embedding-2-preview` | `AIza...` |

---

## 🗄️ Vector Database

| Variable | Description | Example |
| :--- | :--- | :--- |
| `QDRANT_API_KEY` | Qdrant Cloud access token | `xyz...` |
| `QDRANT_CLUSTER_ENDPOINT` | Full URL of your Qdrant Cloud cluster | `https://your-cluster.cloud.qdrant.io:6333` |

---

## 🕵️ Observability

| Variable | Description | Example |
| :--- | :--- | :--- |
| `LOGFIRE_TOKEN` | Pydantic Logfire token — traces every API call, parsing step, and retrieval span | `logfire_...` |
| `LANGSMITH_API_KEY` | LangSmith token — records LangGraph node transitions, prompts, and token usage | `lsv2_...` |
| `LANGSMITH_PROJECT` | LangSmith project name to group traces | `enterprise_rag` |
| `LANGSMITH_TRACING` | Enable/disable LangSmith tracing | `true` |
| `LANGSMITH_ENDPOINT` | LangSmith API endpoint | `https://api.smith.langchain.com` |

---

## 🧪 Evals

| Variable | Description | Example |
| :--- | :--- | :--- |
| `JUDGE_GROQ` | Separate Groq key used exclusively by the RAGAS eval pipeline as the judge LLM. Keeping it separate ensures eval runs cannot exhaust the production key. | `gsk_...` |

---

## 🖥️ Backend

| Variable | Description | Example |
| :--- | :--- | :--- |
| `BACKEND_URL` | URL the Streamlit UI uses to reach the FastAPI backend | `http://localhost:8000` |

---

## 🔒 Security Best Practices
1.  **Never** commit your `.env` file to Git — it is in `.gitignore`.
2.  Use `.env.example` as the template when onboarding new developers.
3.  Keep `JUDGE_GROQ` on a separate key so eval workloads cannot rate-limit the live app.

---

## 🧩 Platform (Self-Adaptive RAG)

| Variable | Description | Example |
| :--- | :--- | :--- |
| `JWT_SECRET` | Secret used to sign login JWTs. **Must** be changed in production. | `openssl rand -hex 32` |
| `ADMIN_EMAIL` | Bootstrap admin account seeded on first startup | `admin@company.com` |
| `ADMIN_PASSWORD` | Password for the bootstrap admin | strong password |
| `DB_PATH` | SQLite database file for users/workspaces/documents | `platform.db` |
| `UPLOADS_DIR` | Where uploaded documents are stored | `uploads` |
| `FRONTEND_ORIGIN` | Allowed CORS origin for the React dev server | `http://localhost:5173` |

Notes:
- The admin account is created at startup only if the email doesn't exist; an existing account with that email is promoted to admin.
- Registration via the UI always creates a `user` (non-admin) account.
- The LLM gateway now uses Groq `openai/gpt-oss-120b` (primary) → `openai/gpt-oss-20b` (fallback); `GROQ_SLUG_2` may hold the literal placeholder `GROQ_SLUG` in older `.env` files — the gateway falls back through the primary virtual key in that case.
