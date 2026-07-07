# skills/rag_skill.py
import os
import re
from flask import request, has_request_context
from .base_skill import Skill
from session_context import get_session_context
from rag.retriever import retrieve_context
from rag.vector_store import SessionVectorStore, DOCS_DIR
from services import llm_service

class RAGSkill(Skill):
    def intents(self):
        return ["notes", "document", "documents", "my notes", "my document"]

    def handle(self, command, doc):
        session_context = get_session_context()
        session_id = request.sid if (has_request_context() and hasattr(request, 'sid') and request.sid) else "default_session"
        
        # Clean query: strip trigger words and boilerplate phrasing
        clean_query = command.lower()
        clean_query = re.sub(r"\b(search|explain|tell me about|what does|what do|say about|from|in)\b", "", clean_query)
        clean_query = re.sub(r"\b(my notes|my documents|my document|notes|documents|uploaded files|uploaded file)\b", "", clean_query)
        clean_query = clean_query.strip()
        if not clean_query:
            clean_query = command
            
        # Check if vector store is initialized or has documents
        store = SessionVectorStore(session_id)
        session_docs_dir = os.path.join(DOCS_DIR, session_id)
        if store.index.ntotal == 0:
            if not os.path.exists(session_docs_dir) or not os.listdir(session_docs_dir):
                return "You haven't uploaded any documents yet. Please use the upload widget to add some notes.", "IDLE"
                
        # Retrieve context matching clean_query
        chunks = retrieve_context(clean_query, session_id, k=3)
        if not chunks:
            return "I couldn't find any relevant information in your notes regarding that topic.", "IDLE"
            
        # Call LLM with the context chunks
        prompt = (
            f"User Query: {command}\n\n"
            f"Here are the relevant snippets from the user's uploaded documents:\n"
            + "\n---\n".join(chunks)
            + "\n---\n"
            "Please answer the user's query using ONLY the provided document snippets. "
            "If the document snippets do not contain the answer, state that the information is not in the notes."
        )
        
        # Pass conversational turns and existing summary for multi-turn conversational flow
        history = session_context.get('history', [])
        summary = session_context.get('summary')
        
        response, tokens_used, latency = llm_service.ask(prompt, history, summary)
        
        # Save metrics to context for log_metric retrieval in assistant.py
        session_context['llm_latency'] = latency
        session_context['llm_tokens_used'] = tokens_used
        session_context['is_rag_query'] = 1
        
        return response, "IDLE"
