from typing import TypedDict, List, Annotated, Optional
import operator


class AgentState(TypedDict):
    # Using Annotated with operator .add ensures that messages
    # are appended to the history rather than replaced
    messages: Annotated[List[dict], operator.add]
    current_query: str
    # Explicit routing decision set by the planner — the graph routes on this
    # instead of comparing free-form strings ("CONVERSATIONAL") on current_query
    intent: str  # "conversational" | "retrieval"
    # Standalone search query produced by the rewriter (follow-ups resolved)
    search_query: str
    documents: List[str]
    # Chunks the grader judged relevant — the responder only sees these
    graded_documents: List[str]
    plan: List[str]
    status: str
    final_answer: str
    # Loop guards (hard-capped by the graph's conditional edges)
    retrieval_attempts: int  # how many times retriever has run
    answer_revision: int     # how many times the answer has been regenerated
    verified: bool           # verifier verdict for the final answer
    regenerate: bool         # verifier flagged the answer for one regeneration
    # Compact summary of a long conversation, produced by the condenser
    condensed_history: str
    # Platform context: which workspace collection to search and its learned profile
    workspace_id: Optional[str]
    collection: Optional[str]
    profile: Optional[dict]
