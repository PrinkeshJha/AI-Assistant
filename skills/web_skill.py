import webbrowser
import wikipedia
from .base_skill import Skill

class WebSkill(Skill):
    def intents(self):
        return ["open", "search", "what is", "who is"]

    def handle(self, command, doc):
        if "open google" in command:
            webbrowser.open("https://google.com")
            return "Opening Google.", "IDLE"
        elif "open youtube" in command:
            webbrowser.open("https://youtube.com")
            return "Opening YouTube.", "IDLE"
        else: 
            query = command.replace("search for", "").replace("what is", "").replace("who is", "").strip()
            try:
                # --- SAVING CONTEXT ---
                potential_subjects = [ent.text for ent in doc.ents if ent.label_ in ["PERSON", "ORG", "GPE"]]
                if potential_subjects:
                    self.assistant.conversation_context['last_subject'] = potential_subjects[0]
                    print(f"Context saved: last_subject = {potential_subjects[0]}")
                
                result = wikipedia.summary(query, sentences=2)
                return f"According to Wikipedia... {result}", "IDLE"
            except Exception:
                return f"Sorry, I could not find any results for {query} on Wikipedia.", "IDLE"



