import logfire
from app.agents.nodes.common import format_history, last_user_message
from app.agents.prompts import (
    build_conversational_prompt,
    build_no_context_prompt,
    build_responder_prompt,
)
from app.agents.state import AgentState
from app.gateway import chat_completion, extract_cache_status

STRICT_REVISION_NOTE = (
    "\n\nIMPORTANT: Your previous answer was NOT fully grounded in the context. "
    "Rewrite it using ONLY the KNOWLEDGE BASE CONTEXT. Omit every claim that is "
    "not directly supported by it."
)


def generate_node(state: AgentState):
    """
    Answer synthesis. Three branches:
    - conversational: answers from memory only (no verification downstream)
    - no relevant context: honest refusal instead of a hallucination
    - retrieval: answers strictly from the grader-approved chunks
    The persona and answer style come from the workspace's learned profile.
    """
    history_str = format_history(state["messages"])
    user_msg = last_user_message(state["messages"])
    intent = state.get("intent", "retrieval")

    if intent == "conversational":
        logfire.info("Generating Conversational response using memory.")
        prompt = build_conversational_prompt(state.get("condensed_history", ""), history_str, user_msg)
        no_claims = True  # nothing grounded to verify
    elif not state.get("graded_documents"):
        logfire.info("No relevant context after grading — answering honestly.")
        prompt = build_no_context_prompt(history_str, user_msg, state.get("profile"))
        no_claims = True  # an honest refusal makes no factual claims
    else:
        logfire.info("Generating RAG response from graded knowledge base context.")
        max_context_chars = 12000
        full_context = ""
        for doc in state["graded_documents"]:
            if len(full_context) + len(doc) < max_context_chars:
                full_context += doc + "\n\n"
            else:
                logfire.warning("Context truncated to fit LLM token limits.")
                break

        prompt = build_responder_prompt(
            full_context,
            state.get("condensed_history", ""),
            history_str,
            user_msg,
            state.get("profile"),
        )
        if state.get("regenerate"):
            prompt += STRICT_REVISION_NOTE

    with logfire.span(" LLM Synthesis"):
        try:
            response = chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            content = response.choices[0].message.content
            cache_status = extract_cache_status(response)
            is_cache_hit = cache_status == "HIT"

            if is_cache_hit:
                logfire.info(" Gateway Cache Hit - response served from Portkey cache.")
                plan_update = state["plan"] + ["Cache: Hit "]
                status = "Cache hit - instant response"
            else:
                logfire.info("Response synthesised via LLM.")
                plan_update = state["plan"]
                status = "Response generated."

            update = {
                "final_answer": content,
                "status": status,
                "plan": plan_update,
            }
            if no_claims:
                # conversational answers / honest refusals assert nothing about
                # the corpus — mark them verified so they don't wear the warning
                update["verified"] = True
            if state.get("regenerate"):
                # Consumed the verifier's one regeneration slot
                update["answer_revision"] = state.get("answer_revision", 0) + 1
                update["regenerate"] = False
            return update

        except Exception as e:
            logfire.error(f"LLM Generation failed: {e}")
            raise e


def persist_answer_node(state: AgentState):
    """
    Runs once after a final (verified / conversational / refusal) answer exists,
    recording it in conversation memory. Keeps unverified intermediate drafts
    out of the history.
    """
    return {"messages": [{"role": "assistant", "content": state["final_answer"]}]}
