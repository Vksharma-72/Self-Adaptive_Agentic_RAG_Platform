import logfire

from app.agents.nodes.common import MAX_ANSWER_REVISIONS
from app.agents.prompts import build_verifier_prompt
from app.agents.state import AgentState
from app.gateway import chat_completion


def verify_answer_node(state: AgentState):
    """
    Answer Verifier (Self-RAG): checks the draft answer is fully supported by
    the graded context. Unsupported answers get one regeneration chance
    (handled by the graph's conditional edge) before being returned as-is.
    """
    answer = state.get("final_answer", "")
    context = "\n\n".join(state.get("graded_documents", []))

    if not answer or not context:
        return {
            "verified": True,  # nothing to verify against (e.g. honest refusal)
            "plan": state["plan"] + ["Verification skipped (no context)"],
        }

    prompt = build_verifier_prompt(context, answer)

    with logfire.span(" Answer Verifier"):
        try:
            response = chat_completion(
                [{"role": "user", "content": prompt}], temperature=0.0
            )
            verdict = response.choices[0].message.content.strip().upper()
        except Exception as e:
            logfire.error(f"Verifier failed, accepting answer: {e}")
            verdict = "SUPPORTED"

    supported = "UNSUPPORTED" not in verdict
    logfire.info(f"Verifier verdict: {'SUPPORTED' if supported else 'UNSUPPORTED'}")

    plan_step = "Answer verified against sources" if supported else "Answer NOT grounded — retrying"
    update = {
        "verified": supported,
        "plan": state["plan"] + [plan_step],
        "status": "Answer verified." if supported else "Answer failed verification.",
    }
    if not supported:
        # One regeneration is allowed (the responder answers more strictly when
        # 'regenerate' is set); the graph routes back only while this is True
        update["regenerate"] = state.get("answer_revision", 0) < MAX_ANSWER_REVISIONS
    return update
