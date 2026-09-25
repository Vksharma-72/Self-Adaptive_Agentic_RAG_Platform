# ============================================================
# Multi-stage build:
#   1. Node stage  — builds the React SPA into frontend/dist
#   2. Python stage — FastAPI backend serves both the API and the SPA
# ============================================================

# ---------- Stage 1: frontend build ----------
FROM node:22-slim AS frontend-build

WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build


# ---------- Stage 2: backend ----------
FROM python:3.11-slim-bookworm

# Patch OS-level CVEs, then install system deps required by torch and native packages
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    gcc g++ libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first so pip install is a cached layer.
# Re-runs only when requirements-prod.txt changes, not on every code change.
COPY requirements-prod.txt .
RUN pip install --no-cache-dir --prefer-binary -r requirements-prod.txt

# Copy only the app package — everything else (evals/, DATA/, DOCS/) stays out
COPY app/ ./app/

# Serve the built React SPA from the same uvicorn process
COPY --from=frontend-build /build/dist ./frontend/dist

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
