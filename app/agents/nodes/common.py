"""Shared helpers and pipeline constants for agent nodes."""

# Hard caps for the pipeline's retry loops (enforced by graph routing)
MAX_RETRIEVAL_ATTEMPTS = 2
MAX_ANSWER_REVISIONS = 1


def format_history(messages: list[dict], exclude_last: bool = True) -> str:
    """Renders the conversation as 'Role: text' lines for prompts."""
    msgs = messages[:-1] if exclude_last else messages
    lines = []
    for msg in msgs:
        role = "User" if msg["role"] == "user" else "Assistant"
        lines.append(f"{role}: {msg['content']}")
    return "\n".join(lines)


def last_user_message(messages: list[dict]) -> str:
    return messages[-1]["content"] if messages else ""
