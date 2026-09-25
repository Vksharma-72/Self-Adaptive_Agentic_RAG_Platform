import logfire

from app.agents.nodes.common import format_history
from app.agents.prompts import build_condense_prompt
from app.agents.state import AgentState
from app.gateway import chat_completion

# Below this many messages the full history is small enough to use directly
CONDENSE_THRESHOLD = 10
MAX_RAW_CHARS = 8000


def condense_history_node(state: AgentState):
    """
    Memory Condenser: for long conversations, compresses the history into a
    compact summary once, so every later agent prompt stays small. Short
    conversations pass through untouched (the raw history is used directly).
    """
    history = format_history(state["messages"])

    if len(state["messages"]) <= CONDENSE_THRESHOLD:
        return {"plan": state["plan"] + ["Memory: using full history"]}

    prompt = build_condense_prompt(history[:MAX_RAW_CHARS])

    with logfire.span(" Memory Condenser"):
        try:
            response = chat_completion([{"role": "user", "content": prompt}], temperature=0.2)
            summary = response.choices[0].message.content.strip()
        except Exception as e:
            logfire.error(f"Condenser failed, using truncated history: {e}")
            summary = ""

    if summary:
        logfire.info(f"Conversation condensed to {len(summary)} chars.")
        return {
            "condensed_history": summary,
            "plan": state["plan"] + [f"Memory: conversation condensed ({len(summary)} chars)"],
        }

    return {"plan": state["plan"] + ["Memory: using truncated history"]}
