from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app.agents.state import AgentState
from app.agents.nodes.common import MAX_RETRIEVAL_ATTEMPTS
from app.agents.nodes.planner import planner_node
from app.agents.nodes.condenser import condense_history_node
from app.agents.nodes.rewriter import rewrite_query_node
from app.agents.nodes.retriever import retrieve_node
from app.agents.nodes.grader import grade_documents_node
from app.agents.nodes.responder import generate_node, persist_answer_node
from app.agents.nodes.verifier import verify_answer_node

# 1. Initialize the State Graph
workflow = StateGraph(AgentState)

# 2. Define the Nodes
workflow.add_node("planner", planner_node)
workflow.add_node("condenser", condense_history_node)
workflow.add_node("rewriter", rewrite_query_node)
workflow.add_node("retriever", retrieve_node)
workflow.add_node("grader", grade_documents_node)
workflow.add_node("responder", generate_node)
workflow.add_node("verifier", verify_answer_node)
workflow.add_node("persist", persist_answer_node)

workflow.set_entry_point("planner")
workflow.add_edge("planner", "condenser")


def route_after_condenser(state: AgentState):
    return "responder" if state.get("intent") == "conversational" else "rewriter"


def route_after_grader(state: AgentState):
    if state.get("graded_documents"):
        return "responder"
    # Nothing relevant — broaden the query and search once more
    if state.get("retrieval_attempts", 0) < MAX_RETRIEVAL_ATTEMPTS:
        return "rewriter"
    return "responder"  # responder will answer honestly: not in the KB


def route_after_responder(state: AgentState):
    # Conversational answers and honest refusals have no context to verify against
    if state.get("intent") == "conversational" or not state.get("graded_documents"):
        return "persist"
    return "verifier"


def route_after_verifier(state: AgentState):
    if state.get("verified") or not state.get("regenerate"):
        return "persist"
    return "responder"


# 3. Edges & routing (with hard-capped retry loops)
workflow.add_conditional_edges(
    "condenser", route_after_condenser, {"responder": "responder", "rewriter": "rewriter"}
)
workflow.add_edge("rewriter", "retriever")
workflow.add_edge("retriever", "grader")
workflow.add_conditional_edges(
    "grader", route_after_grader, {"responder": "responder", "rewriter": "rewriter"}
)
workflow.add_conditional_edges(
    "responder", route_after_responder, {"verifier": "verifier", "persist": "persist"}
)
workflow.add_conditional_edges(
    "verifier", route_after_verifier, {"responder": "responder", "persist": "persist"}
)
workflow.add_edge("persist", END)

# ----- MEMORY UPGRADE ------
# MemorySaver allows the agent to remember conversations based on 'thread_id'
checkpointer = MemorySaver()

# 4. Compile the Graph with Memory
rag_agent = workflow.compile(checkpointer=checkpointer)
