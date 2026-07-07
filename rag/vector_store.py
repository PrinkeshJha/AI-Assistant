# rag/vector_store.py
import os
import json
import faiss
import numpy as np

DOCS_DIR = "documents"

class SessionVectorStore:
    def __init__(self, session_id: str, dimension=384):
        self.session_id = session_id
        self.dimension = dimension
        self.index_path = os.path.join(DOCS_DIR, f"index_{session_id}.faiss")
        self.map_path = os.path.join(DOCS_DIR, f"map_{session_id}.json")
        
        os.makedirs(DOCS_DIR, exist_ok=True)
        
        if os.path.exists(self.index_path) and os.path.exists(self.map_path):
            try:
                self.index = faiss.read_index(self.index_path)
                with open(self.map_path, "r", encoding="utf-8") as f:
                    self.doc_map = json.load(f)
            except Exception:
                # Fallback to empty if read fails
                self.index = faiss.IndexFlatIP(dimension)
                self.doc_map = {}
        else:
            self.index = faiss.IndexFlatIP(dimension)
            self.doc_map = {} # Maps string index to doc chunk text

    def add_chunks(self, chunks: list[str], embeddings):
        if not chunks:
            return
            
        # Convert embeddings to numpy array
        if hasattr(embeddings, 'cpu'):
            embeddings_np = embeddings.cpu().numpy()
        else:
            embeddings_np = np.array(embeddings)
            
        embeddings_np = embeddings_np.astype('float32')
        if len(embeddings_np.shape) == 1:
            embeddings_np = np.expand_dims(embeddings_np, axis=0)
            
        # Normalize for cosine similarity via Inner Product Index
        faiss.normalize_L2(embeddings_np)
        
        start_id = self.index.ntotal
        self.index.add(embeddings_np)
        
        for i, chunk in enumerate(chunks):
            self.doc_map[str(start_id + i)] = chunk
            
        # Persist to disk
        faiss.write_index(self.index, self.index_path)
        with open(self.map_path, "w", encoding="utf-8") as f:
            json.dump(self.doc_map, f, ensure_ascii=False, indent=2)

    def search(self, query_embedding, k=3) -> list[str]:
        if self.index.ntotal == 0:
            return []
            
        if hasattr(query_embedding, 'cpu'):
            query_np = query_embedding.cpu().numpy()
        else:
            query_np = np.array(query_embedding)
            
        query_np = query_np.astype('float32')
        if len(query_np.shape) == 1:
            query_np = np.expand_dims(query_np, axis=0)
            
        faiss.normalize_L2(query_np)
        
        distances, indices = self.index.search(query_np, k)
        
        results = []
        for idx in indices[0]:
            if idx != -1 and str(idx) in self.doc_map:
                results.append(self.doc_map[str(idx)])
        return results
