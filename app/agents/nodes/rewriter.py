import json
import logfire

from app.agents.nodes.common import format_history, last_user_message
from app.agents.prompts import build_rewriter_prompt
from app.agents.state import AgentState
from app.gateway import chat_completion


def rewrite_query_node(state: AgentState):
    """
    Query Rewriter: turns the latest message + conversation context into one
    standalone search query. On retrieval retries it deliberately rephrases
    more broadly, since the previous query found nothing relevant.
    """
    profile = state.get("profile")
    is_retry = state.get("retrieval_attempts", 0) > 0

    prompt = build_rewriter_prompt(
        condensed_history=state.get("condensed_history", ""),
        raw_history=format_history(state["messages"]),
        user_message=last_user_message(state["messages"]),
        profile=profile,
        is_retry=is_retry,
    )

    with logfire.span(" Query Rewriter"):
        response = chat_completion([{"role": "user", "content": prompt}], temperature=0.1)
        search_query = response.choices[0].message.content.strip().strip('"')
        # Guard against chatty models that refuse to output a bare query
        if not search_query or len(search_query) > 500:
            search_query = last_user_message(state["messages"])

    logfire.info(f"Search query rewritten: {search_query!r}")

    step = "Retrieval retry: query broadened" if is_retry else "Query rewritten for search"
    return {
        "search_query": search_query,
        "current_query": search_query,
        "status": f"Searching for: {search_query}",
        "plan": state["plan"] + [f"{step}: {search_query}"],
    }
