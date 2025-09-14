import pyjokes
from .base_skill import Skill

class FunSkill(Skill):
    def intents(self):
        return ["joke"]
    
    def handle(self, command, doc):
        return pyjokes.get_joke(), "IDLE"