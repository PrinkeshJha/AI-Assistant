from .base_skill import Skill

class ControlSkill(Skill):
    def intents(self):
        return ["stop", "exit", "quit", "goodbye", "go to sleep"]

    def handle(self, command, doc):
        response = "Goodbye, Sir."
        # This skill is not yet used in the web UI, but is here for future use.
        return response, "IDLE"