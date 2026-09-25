"""
End-to-end verification of the self-adaptive platform with a LOCAL Qdrant
(the user's Qdrant Cloud endpoint is currently unreachable from this machine).

Runs the real flow: admin login -> create workspace -> upload real documents ->
background ingestion (real Gemini embeddings) -> LLM corpus analysis ->
guardrail generation -> authenticated chat (on-topic + off-topic).
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["LOGFIRE_TOKEN"] = ""

from dotenv import load_dotenv

load_dotenv()

# Patch qdrant_service BEFORE app modules use it: local in-memory Qdrant
from qdrant_client import QdrantClient

import app.services.retrieval.qdrant_service as qservice

qservice.client = QdrantClient(":memory:")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

DATA = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "DATA", "true_data"
)
FILES = ["pods_autoscale.html", "parallel_work_queue.txt", "monitor_job.docx"]

with client:
    # 1. Admin login
    r = client.post(
        "/auth/login",
        data={"username": os.environ["ADMIN_EMAIL"], "password": os.environ["ADMIN_PASSWORD"]},
    )
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    H = {"Authorization": f"Bearer {token}"}
    print("[1] admin login OK")

    # 2. Create workspace
    r = client.post(
        "/workspaces", json={"name": "K8s Job KB", "description": "e2e verification"}, headers=H
    )
    assert r.status_code == 201, r.text
    ws_id = r.json()["id"]
    print(f"[2] workspace created: {ws_id}")

    # 3. Upload real documents
    files = [("files", (f, open(os.path.join(DATA, f), "rb"))) for f in FILES]
    r = client.post(f"/workspaces/{ws_id}/documents", files=files, headers=H)
    assert r.status_code == 201 and not r.json()["rejected"], r.text
    print(f"[3] uploaded {len(r.json()['queued'])} documents")

    # 4. Wait for ingestion + analysis (status: ingesting -> analyzing -> ready)
    for _ in range(60):
        time.sleep(5)
        status = client.get(f"/workspaces/{ws_id}", headers=H).json()["status"]
        docs = client.get(f"/workspaces/{ws_id}/documents", headers=H).json()
        line = ", ".join(f"{d['filename']}:{d['status']}({d['num_chunks']})" for d in docs)
        print(f"    status={status} | {line}")
        if status == "ready":
            break
        if status == "empty" and all(d["status"] in ("failed",) for d in docs):
            raise SystemExit("ingestion failed: " + line)
    assert status == "ready", "workspace never became ready"

    # 5. Inspect the learned profile
    profile = client.get(f"/workspaces/{ws_id}/profile", headers=H).json()["profile"]
    print("[5] learned profile:")
    print(f"    domain:    {profile['domain_name']}")
    print(f"    topics:    {', '.join(profile['topics'][:6])}")
    print(f"    persona:   {profile['persona']}")

    # 6. Chat — on-topic question (corpus is Kubernetes job management docs)
    r = client.post(
        f"/workspaces/{ws_id}/query", json={"q": "How do I monitor and manage jobs in Kubernetes?", "thread_id": "t1"},
        headers=H,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    steps = " ".join(data["thought_process"])
    print(f"[6] on-topic chat -> status={data['status']} verified={data.get('verified')}")
    assert "Grad" in steps, "grader step missing"
    print(f"    agent steps: {[s for s in data['thought_process'] if 'rewrit' in s.lower() or 'Grad' in s or 'erif' in s.lower()]}")
    print(f"    answer: {data['answer'][:180]}...")
    print(f"    sources: {len(data['sources'])} chunks")

    # 6b. On-corpus follow-up using conversation memory
    r = client.post(
        f"/workspaces/{ws_id}/query", json={"q": "and how do I run them in parallel?", "thread_id": "t1"},
        headers=H,
    )
    data = r.json()
    print(f"[6b] follow-up (memory+rewrite) -> status={data['status']} verified={data.get('verified')}")
    print(f"    steps: {data['thought_process'][:6]}")
    print(f"    answer: {data['answer'][:140]}...")

    # 6c. Off-corpus technical question — expect honest refusal or guardrail block
    r = client.post(
        f"/workspaces/{ws_id}/query", json={"q": "How do I configure SRIOV network device plugins?", "thread_id": "t2"},
        headers=H,
    )
    data = r.json()
    honest = "guardrails" in " ".join(data["thought_process"]).lower() or "not" in data["answer"][:200].lower()
    print(f"[6c] off-corpus question -> honest_or_blocked={honest} answer={data['answer'][:100]}")

    # 7. Chat — off-topic question should be blocked by generated guardrails
    r = client.post(
        f"/workspaces/{ws_id}/query", json={"q": "recommend a movie for tonight", "thread_id": "t1"},
        headers=H,
    )
    data = r.json()
    blocked = "guardrails" in " ".join(data["thought_process"]).lower()
    print(f"[7] off-topic chat -> blocked={blocked} answer={data['answer'][:100]}")

    print("\nE2E VERIFICATION COMPLETE")
