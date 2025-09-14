# assistant.py
import importlib
import os
import sys
from typing import Optional

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
            return "Yes, Sir?", "AWAKE"

        if WAKE_WORD in command_lower:
            command_lower = command_lower.replace(WAKE_WORD, "").strip()

        doc = self.nlp(command_lower)
        
        for skill in self.skills:
            for intent in skill.intents():
                if intent in doc.text:
                    response, new_state = skill.handle(command_lower, doc)
                    return response, new_state
        
        return "I'm not sure how to help with that yet.", "IDLE"