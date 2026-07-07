# rag/retriever.py
from rag.embeddings import get_embeddings
from rag.vector_store import SessionVectorStore

def retrieve_context(query: str, session_id: str, k=3) -> list[str]:
    """
    Retrieves top-k context chunks for a query from the session-scoped vector store.
    """
    store = SessionVectorStore(session_id)
    if store.index.ntotal == 0:
        return []
    
    query_emb = get_embeddings([query])
    # The embeddings model returns a batch, grab the first element
    if len(query_emb) > 0:
        return store.search(query_emb[0], k=k)
    return []
