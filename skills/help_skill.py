from .base_skill import Skill

class HelpSkill(Skill):
    """A skill to dynamically list all available commands."""
    def intents(self):
        return ["help", "what can you do", "commands"]

    def handle(self, command, doc):
        help_message = "Here are some of the things you can ask me to do:<br><br>"
        
        all_intents = []
        for skill in self.assistant.skills:
            if isinstance(skill, HelpSkill):
                continue
            all_intents.extend(skill.intents())
            
        unique_intents = sorted(list(set(all_intents)))
        
        formatted_intents = [f"• Tell me the <strong>{intent}</strong>" for intent in unique_intents if len(intent) > 3]
        
        help_message += "<br>".join(formatted_intents)
        
        return help_message, "IDLE"