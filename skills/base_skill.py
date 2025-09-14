from abc import ABC, abstractmethod

class Skill(ABC):
    """Abstract base class for all skills."""
    def __init__(self, assistant):
        self.assistant = assistant

    @abstractmethod
    def intents(self):
        """Returns a list of keywords that trigger this skill."""
        pass

    @abstractmethod
    def handle(self, command, doc):
        """Handles the command and returns a (response, state) tuple."""
        pass