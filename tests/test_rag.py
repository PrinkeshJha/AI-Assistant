import pytest
import os
import shutil
from rag.chunking import split_text
from rag.embeddings import get_embeddings
from rag.vector_store import SessionVectorStore, DOCS_DIR
from rag.retriever import retrieve_context

def test_chunking():
    text = "one two three four five six seven eight nine ten"
    # test chunking with 4 words size and 1 word overlap
    chunks = split_text(text, chunk_size=4, overlap=1)
    assert len(chunks) == 3
    assert chunks[0] == "one two three four"
    assert chunks[1] == "four five six seven"
    assert chunks[2] == "seven eight nine ten"

def test_rag_flow_and_session_isolation():
    # Clean up test indexes first if exist
    session_a = "session_test_A"
    session_b = "session_test_B"
    
    for sid in [session_a, session_b]:
        idx_path = os.path.join(DOCS_DIR, f"index_{sid}.faiss")
        map_path = os.path.join(DOCS_DIR, f"map_{sid}.json")
        if os.path.exists(idx_path):
            os.remove(idx_path)
        if os.path.exists(map_path):
            os.remove(map_path)
            
    # Add chunks for Session A
    chunks_a = [
        "Quantum computing is a type of computation whose operations can harness the phenomena of quantum mechanics.",
        "Deep learning is part of a broader family of machine learning methods based on artificial neural networks.",
        "The Eiffel Tower is a wrought-iron lattice tower on the Champ de Mars in Paris, France."
    ]
    embs_a = get_embeddings(chunks_a)
    store_a = SessionVectorStore(session_a)
    store_a.add_chunks(chunks_a, embs_a)
    
    # Retrieve from Session A
    res_a = retrieve_context("tell me about the tower in Paris", session_a, k=1)
    assert len(res_a) == 1
    assert "Eiffel Tower" in res_a[0]
    
    # Verify Session Isolation: Session B should return nothing since it's empty
    res_b = retrieve_context("tell me about the tower in Paris", session_b, k=1)
    assert len(res_b) == 0
    
    # Clean up
    for sid in [session_a, session_b]:
        idx_path = os.path.join(DOCS_DIR, f"index_{sid}.faiss")
        map_path = os.path.join(DOCS_DIR, f"map_{sid}.json")
        if os.path.exists(idx_path):
            os.remove(idx_path)
        if os.path.exists(map_path):
            os.remove(map_path)

def test_upload_route():
    from unittest.mock import patch
    import io
    from app import app
    client = app.test_client()
    
    data = {
        'session_id': 'test_upload_session',
        'file': (io.BytesIO(b"Hello world from uploaded text document"), 'test.txt')
    }
    
    with patch("rag.vector_store.SessionVectorStore.add_chunks") as mock_add_chunks, \
         patch("rag.embeddings.get_embeddings", return_value=[[0.1]*384]):
        
        resp = client.post('/upload', data=data, content_type='multipart/form-data')
        assert resp.status_code == 200
        json_data = resp.get_json()
        assert "successfully indexed" in json_data["message"]
        mock_add_chunks.assert_called_once()
        
    shutil.rmtree("documents/test_upload_session", ignore_errors=True)

def test_rag_skill_execution():
    from assistant import JarvisAssistant
    from unittest.mock import patch, MagicMock
    assistant = JarvisAssistant()
    
    mock_store = MagicMock()
    mock_store.index.ntotal = 1
    
    with patch("skills.rag_skill.SessionVectorStore", return_value=mock_store), \
         patch("skills.rag_skill.retrieve_context", return_value=["LR Parsing is bottom-up parsing."]) as mock_retrieve, \
         patch("services.llm_service.ask", return_value=("According to your notes, LR Parsing is bottom-up parsing.", 30, 0.15)) as mock_ask:
        
        with patch.object(assistant.classifier, "classify", return_value={"RAGSkill": 0.8}):
            res, state = assistant.process_command("explain LR parsing from my notes")
            assert "bottom-up parsing" in res
            assert state == "IDLE"
            mock_retrieve.assert_called_once()
            mock_ask.assert_called_once()

def test_documents_list_and_delete():
    from app import app
    import os
    import shutil
    
    client = app.test_client()
    session_id = "test_list_delete_session"
    session_docs_dir = os.path.join("documents", session_id)
    os.makedirs(session_docs_dir, exist_ok=True)
    
    # Create two mock files
    file1_path = os.path.join(session_docs_dir, "doc1.txt")
    file2_path = os.path.join(session_docs_dir, "doc2.txt")
    
    with open(file1_path, "w", encoding="utf-8") as f:
        f.write("content of doc one")
    with open(file2_path, "w", encoding="utf-8") as f:
        f.write("content of doc two")
        
    try:
        # Rebuild index for these two files
        from app import rebuild_session_index
        rebuild_session_index(session_id)
        
        # Test listing
        resp = client.get(f'/documents?session_id={session_id}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data['documents']) == 2
        names = [d['name'] for d in data['documents']]
        assert "doc1.txt" in names
        assert "doc2.txt" in names
        
        # Test deleting one document
        resp_del = client.delete(f'/documents?session_id={session_id}&filename=doc1.txt')
        assert resp_del.status_code == 200
        del_data = resp_del.get_json()
        assert "deleted and index rebuilt successfully" in del_data['message']
        
        # Verify it was deleted from list
        resp_list = client.get(f'/documents?session_id={session_id}')
        assert resp_list.status_code == 200
        list_data = resp_list.get_json()
        assert len(list_data['documents']) == 1
        assert list_data['documents'][0]['name'] == "doc2.txt"
        
        # Verify physical file deletion
        assert not os.path.exists(file1_path)
        assert os.path.exists(file2_path)
    finally:
        shutil.rmtree(session_docs_dir, ignore_errors=True)
        # Clean up index files
        idx_path = os.path.join("documents", f"index_{session_id}.faiss")
        map_path = os.path.join("documents", f"map_{session_id}.json")
        if os.path.exists(idx_path):
            os.remove(idx_path)
        if os.path.exists(map_path):
            os.remove(map_path)
