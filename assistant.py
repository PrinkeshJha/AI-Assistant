# assistant.py
import importlib
import logging
import os
import re
import sys
import time
from typing import Optional, Dict, Any

from session_context import get_session_context, clear_session_context
from classifier.embedding_classifier import EmbeddingClassifier
from context.context_manager import (
    resolve_pronouns,
    is_ellipsis_or_fragment,
    merge_context,
    update_entities_from_doc,
    add_to_history
)
from analytics.metrics import log_metric
from services import llm_service

import spacy

from config import WAKE_WORD, ASSISTANT_NAME

if sys.version_info >= (3, 8):
    from typing import Protocol
    class Skill(Protocol):
        def intents(self) -> list[str]: ...
        def handle(self, command: str, doc) -> tuple[str, str]: ...
else:
    from skills.base_skill import Skill

class JarvisAssistant:
    def __init__(self):
        self.name = ASSISTANT_NAME
        self.nlp = spacy.load("en_core_web_sm")
        
        # Setup logging
        os.makedirs("logs", exist_ok=True)
        self.logger = logging.getLogger("JarvisAssistant")
        if not self.logger.handlers:
            handler = logging.FileHandler("logs/assistant.log", encoding="utf-8")
            handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        self.skills: list[Skill] = self._load_skills()
        self.classifier = EmbeddingClassifier()

    def _check_and_summarize(self, session_context):
        history = session_context.get('history', [])
        if len(history) >= 5:
            try:
                self.logger.info("Turn history threshold reached (>= 5). Summarizing conversation...")
                existing_summary = session_context.get('summary')
                new_summary = llm_service.summarize_history(history, existing_summary)
                session_context['summary'] = new_summary
                # Keep only the last turn to maintain continuity
                session_context['history'] = history[-1:]
                self.logger.info(f"Summarization completed. New summary: {new_summary}")
            except Exception as e:
                self.logger.error(f"Error during context summarization: {e}")

    def _load_db_history(self, conversation_id, limit=10):
        from models import Message
        messages = Message.query.filter_by(conversation_id=conversation_id).order_by(Message.timestamp.asc()).all()
        turns = []
        current_turn = None
        for msg in messages:
            if msg.sender == 'user':
                if current_turn:
                    turns.append(current_turn)
                current_turn = {
                    'query': msg.text,
                    'response': '',
                    'intent': msg.source or 'None',
                    'entities': []
                }
            elif msg.sender == 'assistant':
                if current_turn:
                    current_turn['response'] = msg.text
                    current_turn['intent'] = msg.source or 'None'
                    turns.append(current_turn)
                    current_turn = None
        if current_turn:
            turns.append(current_turn)
        return turns[-limit:]

    def _save_db_message(self, session_context, query, response):
        from flask import has_app_context
        conv_id = session_context.get('active_conversation_id')
        if conv_id and has_app_context():
            try:
                from models import db, Message
                user_msg = Message(
                    conversation_id=conv_id,
                    sender='user',
                    text=query,
                    source='user',
                    confidence=1.0
                )
                assistant_msg = Message(
                    conversation_id=conv_id,
                    sender='assistant',
                    text=response,
                    source=session_context.get('last_source', 'skill'),
                    confidence=session_context.get('last_confidence', 1.0)
                )
                db.session.add(user_msg)
                db.session.add(assistant_msg)
                db.session.commit()
            except Exception as e:
                self.logger.error(f"Error saving message to DB: {e}")



    def _load_skills(self) -> list[Skill]:
        skills = []
        skills_dir = 'skills'
        for filename in os.listdir(skills_dir):
            if filename.endswith('_skill.py') and filename != 'base_skill.py':
                module_name = f"{skills_dir}.{filename[:-3]}"
                try:
                    module = importlib.import_module(module_name)
                    for item in dir(module):
                        obj = getattr(module, item)
                        if isinstance(obj, type) and obj.__module__ == module_name:
                            skills.append(obj(self))
                except Exception as e:
                    print(f"Error loading skill from {filename}: {e}")
        print(f"Loaded {len(skills)} skills.")
        return skills

    def process_command(self, command: str) -> tuple[str, str]:
        command_lower = command.lower()

        if WAKE_WORD in command_lower and len(command_lower.replace(WAKE_WORD, "").strip()) < 4:
            clear_session_context()
            # Initialize context to set source/confidence
            ctx = get_session_context()
            ctx['last_source'] = 'skill'
            ctx['last_confidence'] = 1.0
            return "Yes, Sir?", "AWAKE"

        # Construct cased command without wake word
        command_processed = command.strip()
        wake_word_idx = command_lower.find(WAKE_WORD)
        if wake_word_idx != -1:
            command_processed = (command[:wake_word_idx] + command[wake_word_idx + len(WAKE_WORD):]).strip()

        session_context = get_session_context()

        # Retrieve previous query history to resolve ellipsis
        conv_id = session_context.get('active_conversation_id')
        from flask import has_app_context
        if conv_id and has_app_context():
            try:
                history = self._load_db_history(conv_id)
            except Exception as e:
                self.logger.error(f"Error loading DB history: {e}")
                history = session_context.get('history', [])
        else:
            history = session_context.get('history', [])
        prev_query = history[-1]['query'] if history else None

        # 1. Resolve pronouns
        command_resolved = resolve_pronouns(command_processed, session_context)
        if command_resolved != command_processed:
            print(f"Injecting context (pronouns). New command: '{command_resolved}'")
            self.logger.info(f"Pronoun resolved: '{command_processed}' -> '{command_resolved}'")

        # 2. Resolve ellipsis/fragments
        if prev_query and is_ellipsis_or_fragment(command_resolved, self.nlp):
            command_merged = merge_context(prev_query, command_resolved, self.nlp)
            print(f"Injecting context (ellipsis). New command: '{command_merged}'")
            self.logger.info(f"Ellipsis merged: '{command_resolved}' -> '{command_merged}'")
            command_resolved = command_merged

        doc = self.nlp(command_resolved)

        # 3. Classify query intent using Embedding Classifier
        scores = self.classifier.classify(command_resolved)
        self.logger.info(f"Intent classification scores: {scores}")

        # Rank intents
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        best_intent = None
        best_score = 0.0
        if sorted_scores:
            best_intent, best_score = sorted_scores[0]

        # 4. Handle confidence threshold of 0.65
        if best_score < 0.65:
            # Gather top 2-3 plausible intents (confidence score >= 0.3)
            plausible_intents = [intent for intent, score in sorted_scores if score >= 0.3]
            top_plausible = plausible_intents[:3]

            if len(top_plausible) >= 2:
                if len(top_plausible) == 2:
                    suggestion = f"Did you mean {top_plausible[0]} or {top_plausible[1]}?"
                else:
                    suggestion = f"Did you mean {top_plausible[0]}, {top_plausible[1]}, or {top_plausible[2]}?"
                response = f"I'm not sure. {suggestion}"
                success_status = "CLARIFICATION"
                log_metric(
                    query=command_processed,
                    detected_intent=best_intent if best_intent else "None",
                    confidence=best_score,
                    resolved_skill="None",
                    success_status=success_status
                )
                session_context['last_source'] = 'clarification'
                session_context['last_confidence'] = float(best_score)
                self._save_db_message(session_context, command_processed, response)
                return response, "IDLE"
            else:
                try:
                    summary = session_context.get('summary')
                    response, tokens_used, latency = llm_service.ask(command_resolved, history, summary)
                    success_status = "FALLBACK"
                    
                    update_entities_from_doc(doc, session_context)
                    add_to_history(command_resolved, "LLMFallback", [ent.text for ent in doc.ents], session_context, response)
                    self._check_and_summarize(session_context)
                except Exception as e:
                    self.logger.error(f"LLM fallback failed: {e}", exc_info=True)
                    response = "I'm not sure how to help with that yet."
                    success_status = "FALLBACK"
                    tokens_used, latency = 0, 0.0

                log_metric(
                    query=command_processed,
                    detected_intent=best_intent if best_intent else "None",
                    confidence=best_score,
                    resolved_skill="None",
                    success_status=success_status,
                    llm_latency=latency,
                    llm_tokens_used=tokens_used,
                    is_rag_query=0
                )
                session_context['last_source'] = 'llm'
                session_context['last_confidence'] = float(best_score)
                self._save_db_message(session_context, command_processed, response)
                return response, "IDLE"

        # 5. Dispatch if confidence >= 0.65
        if best_intent:
            for skill in self.skills:
                if skill.__class__.__name__ == best_intent:
                    start_time = time.time()
                    try:
                        # Extract skill response
                        response, new_state = skill.handle(doc.text.lower(), doc)
                        success_status = "SUCCESS"
                        
                        # Store updated context entities and history upon successful execution
                        update_entities_from_doc(doc, session_context)
                        add_to_history(command_resolved, best_intent, [ent.text for ent in doc.ents], session_context, response)
                        self._check_and_summarize(session_context)
                    except Exception as e:
                        self.logger.error(f"Skill execution failed for {best_intent}: {e}", exc_info=True)
                        response = "Sorry, I encountered an error while processing that request."
                        new_state = "IDLE"
                        success_status = "ERROR"
                    finally:
                        elapsed_ms = (time.time() - start_time) * 1000
                        self.logger.info(f"Skill {skill.__class__.__name__} invoked. Elapsed time: {elapsed_ms:.2f}ms")
                        
                    # Retrieve LLM metrics if populated by RAGSkill or other skills
                    llm_latency = session_context.pop('llm_latency', None)
                    llm_tokens = session_context.pop('llm_tokens_used', None)
                    is_rag = session_context.pop('is_rag_query', 0)
                    
                    log_metric(
                        query=command_processed,
                        detected_intent=best_intent,
                        confidence=best_score,
                        resolved_skill=skill.__class__.__name__,
                        success_status=success_status,
                        llm_latency=llm_latency,
                        llm_tokens_used=llm_tokens,
                        is_rag_query=is_rag
                    )
                    session_context['last_source'] = 'rag' if best_intent == 'RAGSkill' else 'skill'
                    session_context['last_confidence'] = float(best_score)
                    self._save_db_message(session_context, command_processed, response)
                    return response, new_state

        log_metric(
            query=command_processed,
            detected_intent="None",
            confidence=0.0,
            resolved_skill="None",
            success_status="FALLBACK"
        )
        session_context['last_source'] = 'llm'
        session_context['last_confidence'] = 0.0
        response = "I'm not sure how to help with that yet."
        self._save_db_message(session_context, command_processed, response)
        return response, "IDLE"