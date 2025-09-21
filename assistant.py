# assistant.py
import importlib
import os
import sys
from typing import Optional, Dict, Any

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
        # --- CONTEXT HOLDER ---
        self.conversation_context: Dict[str, Any] = {}
        self.skills: list[Skill] = self._load_skills()


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
            self.conversation_context.clear()
            return "Yes, Sir?", "AWAKE"

        if WAKE_WORD in command_lower:
            command_lower = command_lower.replace(WAKE_WORD, "").strip()

        # --- CONTEXT INJECTION LOGIC ---
        doc = self.nlp(command_lower)
        has_pronoun = any(token.pos_ == "PRON" and token.text in ["he", "his", "him", "her", "it", "its"] for token in doc)
        
        if has_pronoun and 'last_subject' in self.conversation_context:
            subject = self.conversation_context['last_subject']
            # Simple pronoun replacement
            command_with_context = command_lower.replace("his", subject).replace("her", subject).replace("its", subject).replace("it", subject).replace("he", subject).replace("him", subject)
            print(f"Injecting context. New command: '{command_with_context}'")
            doc = self.nlp(command_with_context)
        else:
            self.conversation_context.clear()

        for skill in self.skills:
            for intent in skill.intents():
                if intent in doc.text:
                    response, new_state = skill.handle(doc.text, doc)
                    return response, new_state
        
        return "I'm not sure how to help with that yet.", "IDLE"