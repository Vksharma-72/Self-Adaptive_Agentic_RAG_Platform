import logfire

from app.agents.nodes.common import format_history, last_user_message
from app.agents.prompts import build_planner_prompt
from app.agents.state import AgentState
from app.gateway import chat_completion


def planner_node(state: AgentState):
    """
    Pure intent classification: 'conversational' (answerable from memory /
    small talk) vs 'retrieval' (needs the knowledge base). Search-query
    refinement is handled by the dedicated rewriter agent.
    """
    prompt = build_planner_prompt(
        format_history(state["messages"]),
        last_user_message(state["messages"]),
        state.get("profile"),
    )

    with logfire.span(" Planner Decision"):
        response = chat_completion([{"role": "user", "content": prompt}], temperature=0.0)
        decision = response.choices[0].message.content.strip().upper()
        logfire.info(f"Intent identified: {decision}")

    if "CONVERSATIONAL" in decision:
        return {
            "intent": "conversational",
            "current_query": last_user_message(state["messages"]),
            "status": "Handling conversationally (using memory)....",
            "plan": state["plan"] + ["Intent: Conversational/Memory", "Retrieval: Skipped"],
        }

    return {
        "intent": "retrieval",
        "status": "Knowledge base research needed.",
        "plan": state["plan"] + ["Intent: Retrieval from knowledge base"],
    }
