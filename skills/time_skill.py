import datetime
from .base_skill import Skill

class TimeSkill(Skill):
    def intents(self):
        return ["time", "date", "day"]

    def handle(self, command, doc):
        now = datetime.datetime.now()
        if "time" in command:
            response = f"The current time is {now.strftime('%I:%M %p')}."
        elif "date" in command:
            response = f"Today's date is {now.strftime('%B %d, %Y')}."
        elif "day" in command:
            response = f"Today is {now.strftime('%A')}."
        else:
            response = "I can't determine what you're asking about the time."
        return response, "IDLE"