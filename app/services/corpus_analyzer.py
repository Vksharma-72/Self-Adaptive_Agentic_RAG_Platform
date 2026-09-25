import json
import re

import logfire

from app.db.database import SessionLocal
from app.db.models import Workspace
from app.gateway import chat_completion


# How much corpus evidence the analyzer sees per learning pass
MAX_SAMPLE_POINTS = 300
MAX_SAMPLE_CHUNKS = 40
MAX_CHUNK_CHARS = 1200

PROFILE_PROMPT = """
You are a Knowledge Base Analyzer. You build the "knowledge profile" that an
adaptive RAG assistant uses to answer questions about this corpus — including
its own persona, topics, and what counts as off-topic.

CORPUS SAMPLE (chunks sampled from the indexed documents):
{corpus_sample}

EXISTING PROFILE (from a previous learning pass — merge and improve it; keep
anything still accurate):
{existing_profile}

Analyze the corpus and respond with ONLY a valid JSON object (no markdown
fences, no commentary) with exactly these keys:

{{
  "domain_name": "short name for this knowledge domain (2-5 words)",
  "summary": "2-3 sentence description of what the corpus covers",
  "topics": ["6-12 key topic areas the assistant should be able to answer questions about"],
  "terminology": [{{"term": "...", "definition": "one-line definition"}}],
  "audience": "who the corpus is written for",
  "sample_questions": ["6-10 realistic questions this knowledge base can answer"],
  "off_topic_examples": ["6-10 example questions that are NOT covered by this corpus and should be politely refused"],
  "persona": "one-sentence persona description for the assistant (e.g. 'a concise technical support engineer for X')",
  "answer_style": "how answers should be written (tone, length, use of examples/lists)"
}}
"""

MERGE_HINT = "(none — first learning pass)"


def _sample_chunks(collection: str) -> list[str]:
    """Pull an evenly-spread sample of chunk texts from the workspace collection."""
    from app.services.retrieval.qdrant_service import client as qdrant_client

    if not qdrant_client.collection_exists(collection):
        return []

    points, _ = qdrant_client.scroll(
        collection_name=collection,
        limit=MAX_SAMPLE_POINTS,
        with_payload=True,
        with_vectors=False,
    )
    texts = [p.payload.get("text", "") for p in points if p.payload.get("text")]
    if not texts:
        return []

    # Even spread over the corpus instead of the first N chunks
    step = max(1, len(texts) // MAX_SAMPLE_CHUNKS)
    sampled = texts[::step][:MAX_SAMPLE_CHUNKS]
    return [t[:MAX_CHUNK_CHARS] for t in sampled]


def _extract_json(raw: str) -> dict:
    """Parse the profile JSON defensively (LLMs sometimes add fences or prose)."""
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    else:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("No JSON object found in analyzer output")
        text = text[start : end + 1]
    return json.loads(text)


def analyze_workspace(workspace_id: str) -> dict | None:
    """
    The self-adaptation step: sample the indexed corpus, have the LLM build/merge
    the workspace's KnowledgeProfile, persist it, and invalidate cached guardrails.
    """
    db = SessionLocal()
    try:
        ws = db.get(Workspace, workspace_id)
        if ws is None:
            return None

        chunks = _sample_chunks(ws.qdrant_collection)
        if not chunks:
            logfire.warning(f"Analyzer: no indexed chunks found for '{ws.name}'.")
            ws.status = "empty" if not ws.profile_json else "ready"
            db.commit()
            return None

        corpus_sample = "\n\n---\n\n".join(f"[chunk {i+1}]\n{c}" for i, c in enumerate(chunks))
        existing = ws.profile_json or MERGE_HINT

        prompt = PROFILE_PROMPT.format(
            corpus_sample=corpus_sample, existing_profile=existing
        )

        with logfire.span("Corpus Analysis", workspace=ws.name, chunks=len(chunks)):
            response = chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a precise JSON-only analyzer. Output raw JSON only.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
            raw = response.choices[0].message.content
            profile = _extract_json(raw)

        ws.profile_json = json.dumps(profile, ensure_ascii=False)
        ws.status = "ready"
        db.commit()
        logfire.info(
            f"Knowledge profile learned for '{ws.name}': domain='{profile.get('domain_name')}' "
            f"topics={len(profile.get('topics', []))}"
        )

        # Persona/topics changed -> generated guardrail rules must be rebuilt
        from app.guardrails.factory import invalidate_rails

        invalidate_rails(workspace_id)
        return profile

    except Exception as e:
        logfire.error(f"Corpus analysis failed for {workspace_id}: {e}")
        try:
            ws = db.get(Workspace, workspace_id)
            if ws:
                ws.status = "failed"
                db.commit()
        except Exception:
            pass
        return None
    finally:
        db.close()
