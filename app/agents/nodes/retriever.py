import logfire
from app.agents.nodes.common import MAX_RETRIEVAL_ATTEMPTS
from app.agents.state import AgentState
from app.services.retrieval.qdrant_service import search_workspace
from app.services.retrieval.ranking_service import rerank_documents

def retrieve_node(state: AgentState):
    """
    Vector search + semantic reranking against the workspace's own Qdrant
    collection, using the standalone search query produced by the rewriter.
    """
    query = state.get("search_query") or state.get("current_query", "")
    collection = state.get("collection")
    attempts = state.get("retrieval_attempts", 0)

    if not collection:
        logfire.error("Retriever has no collection set — workspace context missing.")
        return {
            "documents": [],
            "retrieval_attempts": attempts + 1,
            "status": "No knowledge base selected.",
            "plan": state['plan'] + ["Retrieval Skipped: no collection"]
        }

    with logfire.span("Knowledge Retrieval"):
        logfire.info(f"Searching Qdrant for: {query}")
        raw_results = search_workspace(query, collection, limit=15)
        logfire.info(f"Retrieved {len(raw_results)}  candidates from Vector DB")

        doc_contents = [doc['content'] for doc in raw_results]

        with logfire.span("Semantic Reranking"):
            rerank_contents = rerank_documents(query, doc_contents, top_n=8)
            logfire.info("Reranking complete. Kept top 8 most relevant chunks.")

        sources = sorted({doc['source'] for doc in raw_results if doc.get('source')})

    plan_update = state['plan'] + [f"Retrieved {len(raw_results)} candidates, reranked to {len(rerank_contents)}"]
    if sources:
        plan_update.append(f"Sources: {', '.join(sources)}")

    return {
        "documents": rerank_contents,
        "retrieval_attempts": attempts + 1,
        "status": "Found relevant context." if raw_results else "No relevant context found.",
        "plan": plan_update
    }
