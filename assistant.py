# assistant.py
import importlib
import os
import re
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

        # Construct cased command without wake word
        command_processed = command.strip()
        wake_word_idx = command_lower.find(WAKE_WORD)
        if wake_word_idx != -1:
            command_processed = (command[:wake_word_idx] + command[wake_word_idx + len(WAKE_WORD):]).strip()

        # --- CONTEXT INJECTION LOGIC ---
        doc = self.nlp(command_processed)
        has_pronoun = any(token.pos_ == "PRON" and token.text.lower() in ["he", "his", "him", "her", "it", "its"] for token in doc)
        
        if has_pronoun and 'last_subject' in self.conversation_context:
            subject = self.conversation_context['last_subject']
            # Regex replacement with word boundaries to avoid replacing parts of other words (e.g. "history")
            command_with_context = command_processed
            for pronoun in ["his", "her", "its", "him", "he", "it"]:
                command_with_context = re.sub(rf"\b{pronoun}\b", subject, command_with_context, flags=re.IGNORECASE)
            print(f"Injecting context. New command: '{command_with_context}'")
            doc = self.nlp(command_with_context)
        else:
            self.conversation_context.clear()

        for skill in self.skills:
            for intent in skill.intents():
                if intent in doc.text.lower():
                    response, new_state = skill.handle(doc.text.lower(), doc)
                    return response, new_state
        
        return "I'm not sure how to help with that yet.", "IDLE"