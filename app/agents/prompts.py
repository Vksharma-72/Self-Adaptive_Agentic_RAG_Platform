"""
Prompt builders that derive the agent's instructions from a workspace's
learned KnowledgeProfile. With no profile yet, sensible generic fallbacks
keep the pipeline working from the very first query.

Used by the multi-agent pipeline: planner (intent), rewriter (standalone
search query), grader (relevance filtering), responder (grounded answer),
verifier (faithfulness check) and the memory condenser.
"""
import json

DEFAULT_TOPICS = "the topics covered by the indexed documents"
DEFAULT_DOMAIN = "the indexed knowledge base"
DEFAULT_PERSONA = "a helpful and professional knowledge assistant"


def _topics_str(profile: dict | None) -> str:
    if not profile:
        return DEFAULT_TOPICS
    topics = [t for t in profile.get("topics", []) if isinstance(t, str) and t.strip()]
    return ", ".join(topics[:10]) if topics else DEFAULT_TOPICS


def _domain_str(profile: dict | None) -> str:
    if not profile:
        return DEFAULT_DOMAIN
    return (profile.get("domain_name") or DEFAULT_DOMAIN).strip()


def build_planner_prompt(history: str, user_message: str, profile: dict | None) -> str:
    topics = _topics_str(profile)
    domain = _domain_str(profile)

    return f"""
    You are an intent classifier for a knowledge assistant.
    Analyze the conversation history and the latest user message.

    CONVERSATION HISTORY:
    {history}

    LATEST MESSAGE:
    "{user_message}"

    Task — decide the intent:
    1. 'CONVERSATIONAL' — greetings, thanks, goodbyes, or questions answerable using ONLY the conversation history above (e.g. "what is my name", "what did you just say").
    2. 'RETRIEVAL' — any substantive question that could plausibly be answered from the {domain} knowledge base (topics: {topics}), or that asks about the world/documents in general.

    Output ONLY 'CONVERSATIONAL' or 'RETRIEVAL'.
    """


def build_condense_prompt(history: str) -> str:
    return f"""
    Condense the conversation below into a compact summary that preserves
    everything needed to answer follow-up questions: the user's goal,
    key facts established, entity names, numbers, and any decisions made.
    Keep it under 200 words. Output ONLY the summary.

    CONVERSATION:
    {history}
    """


def build_rewriter_prompt(
    condensed_history: str,
    raw_history: str,
    user_message: str,
    profile: dict | None,
    is_retry: bool,
) -> str:
    context = condensed_history or raw_history
    domain = _domain_str(profile)

    retry_instruction = (
        """
    IMPORTANT: The previous search query found no relevant documents. Rewrite
    the query with DIFFERENT, broader wording — use alternative terms, drop
    overly specific constraints, and think about how the source documents
    might phrase the concept."""
        if is_retry
        else ""
    )

    return f"""
    You are a Search Query Rewriter for a knowledge base about {domain}.

    CONVERSATION CONTEXT:
    {context or "(no prior context)"}

    LATEST USER MESSAGE:
    "{user_message}"
    {retry_instruction}

    Task: write ONE standalone search query that captures what the user wants
    to know from the knowledge base. Resolve pronouns and abbreviations using
    the conversation context (e.g. "what about its memory?" must become a
    query naming the actual subject). Keep it concise — a phrase or one
    sentence, no explanations.

    Output ONLY the search query.
    """


def build_grader_prompt(search_query: str, chunks: list[str], profile: dict | None) -> str:
    topics = _topics_str(profile)
    numbered = "\n\n".join(f"[{i}] {c[:1200]}" for i, c in enumerate(chunks))
    return f"""
    You are a Document Relevance Grader for a knowledge base (topics: {topics}).

    SEARCH QUERY:
    "{search_query}"

    RETRIEVED CHUNKS:
    {numbered}

    Task: decide which chunks contain information that would help answer the
    search query. Be strict: a chunk is relevant only if it genuinely addresses
    the query's subject. Grading every chunk relevant is NOT helpful.

    Output ONLY a JSON array of the indices of relevant chunks, e.g. [0, 2, 5].
    Output [] if none are relevant.
    """


def build_responder_prompt(
    full_context: str,
    condensed_history: str,
    raw_history: str,
    user_message: str,
    profile: dict | None,
) -> str:
    domain = _domain_str(profile)
    persona = (profile or {}).get("persona") or DEFAULT_PERSONA
    style = (profile or {}).get("answer_style") or (
        "Answer clearly and concisely. Use the provided context; if the context "
        "does not contain the answer, say so honestly."
    )
    history = condensed_history or raw_history

    return f"""
        You are {persona}, answering questions about {domain}.

        Answer style: {style}

        STRICT GROUNDING RULES:
        - Answer ONLY from the KNOWLEDGE BASE CONTEXT below. Never use outside
          knowledge to add facts.
        - If the context does not contain the answer, say so honestly and
          suggest what the user could ask instead.

        KNOWLEDGE BASE CONTEXT:
        {full_context}

        CONVERSATION HISTORY:
        {history}

        USER QUESTION:
        "{user_message}"
        """


def build_no_context_prompt(raw_history: str, user_message: str, profile: dict | None) -> str:
    domain = _domain_str(profile)
    persona = (profile or {}).get("persona") or DEFAULT_PERSONA
    return f"""
        You are {persona} for a knowledge base about {domain}.

        A search of the knowledge base found NO documents relevant to the user's
        question. Respond honestly: say the knowledge base doesn't cover this,
        briefly mention what topics it DOES cover, and do NOT invent an answer.

        CONVERSATION HISTORY:
        {raw_history}

        USER QUESTION:
        "{user_message}"
        """


def build_verifier_prompt(full_context: str, answer: str) -> str:
    return f"""
    You are an Answer Verifier. Check whether the DRAFT ANSWER below is fully
    supported by the CONTEXT.

    CONTEXT:
    {full_context}

    DRAFT ANSWER:
    {answer}

    Rules:
    - 'SUPPORTED' if every factual claim in the answer traces back to the context.
    - 'UNSUPPORTED' if the answer invents facts, adds claims not in the context,
      or contradicts it.

    Output ONLY one word: SUPPORTED or UNSUPPORTED.
    """


def build_conversational_prompt(condensed_history: str, raw_history: str, user_message: str) -> str:
    return f"""
        You are a friendly and helpful AI Assistant.
        Answer the user's latest message using the CONVERSATIONAL HISTORY below.

        CONVERSATIONAL HISTORY:
        {condensed_history or raw_history}

        LATEST MESSAGE:
        "{user_message}"
        """


# Backwards-compatible alias used by evals/legacy code paths
def build_responder_prompt_legacy(full_context, history, user_message, profile):
    return build_responder_prompt(full_context, "", history, user_message, profile)
