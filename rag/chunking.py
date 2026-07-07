# rag/chunking.py

def split_text(text: str, chunk_size=100, overlap=15) -> list[str]:
    """
    Splits text into overlapping chunks based on word count.
    """
    if not text:
        return []
    
    words = text.split()
    if not words:
        return []
        
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end == len(words):
            break
        start += chunk_size - overlap
        
    return chunks
