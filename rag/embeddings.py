# rag/embeddings.py
from classifier.embedding_classifier import get_shared_model

def get_embeddings(texts: list[str]) -> list:
    """
    Computes sentence embeddings for a list of texts using the shared model.
    """
    if not texts:
        return []
    model = get_shared_model()
    # Return as numpy array/tensor directly for FAISS compatibility
    return model.encode(texts, convert_to_tensor=True)
