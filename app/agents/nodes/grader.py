import json
import re

import logfire

from app.agents.prompts import build_grader_prompt
from app.agents.state import AgentState
from app.gateway import chat_completion


def _parse_indices(raw: str, total: int) -> list[int]:
    """Defensively extract the graded indices from the LLM output."""
    text = raw.strip()
    match = re.search(r"\[.*?\]", text, re.DOTALL)
    if not match:
        return []
    try:
        indices = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    return [i for i in indices if isinstance(i, int) and 0 <= i < total]


def grade_documents_node(state: AgentState):
    """
    Document Grader (CRAG): one batched LLM call grades every retrieved chunk.
    Relevant chunks flow to the responder; if nothing is relevant, the graph
    either retries retrieval or forces an honest no-answer.
    """
    documents = state.get("documents", [])
    search_query = state.get("search_query") or state.get("current_query", "")

    if not documents:
        logfire.info("Grader: nothing retrieved to grade.")
        return _graded(state, [], "Nothing retrieved from the knowledge base.")

    prompt = build_grader_prompt(search_query, documents, state.get("profile"))

    with logfire.span(" Document Grader"):
        try:
            response = chat_completion(
                [
                    {"role": "system", "content": "You output raw JSON only."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
            )
            indices = _parse_indices(response.choices[0].message.content, len(documents))
        except Exception as e:
            # Fails open: keep all chunks rather than dropping the answer path
            logfire.error(f"Grader failed, keeping all chunks: {e}")
            indices = list(range(len(documents)))

    graded = [documents[i] for i in indices] if indices else []
    logfire.info(f"Grader kept {len(graded)}/{len(documents)} chunks.")

    return _graded(
        state,
        graded,
        f"Graded {len(documents)} retrieved chunks → {len(graded)} relevant.",
    )


def _graded(state: AgentState, graded: list[str], step: str) -> dict:
    return {
        "graded_documents": [f"CONTENT: {c}" for c in graded],
        "plan": state["plan"] + [step],
        "status": step,
    }
