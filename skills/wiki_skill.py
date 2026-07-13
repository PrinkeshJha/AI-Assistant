import wikipedia
from .base_skill import Skill
from session_context import get_session_context
from services.wiki_service import fetch_wiki_summary

class WikiSkill(Skill):
    def intents(self):
        return ["open", "search", "what is", "who is"]

    def handle(self, command, doc):
        if "open google" in command:
            return "[ACTION:OPEN_URL] https://google.com", "IDLE"
        elif "open youtube" in command:
            return "[ACTION:OPEN_URL] https://youtube.com", "IDLE"

        else: 
            query = command.replace("search for", "").replace("what is", "").replace("who is", "").strip()
            try:
                # --- SAVING CONTEXT ---
                potential_subjects = [ent.text for ent in doc.ents if ent.label_ in ["PERSON", "ORG", "GPE"]]
                if potential_subjects:
                    get_session_context()['last_subject'] = potential_subjects[0]
                    print(f"Context saved: last_subject = {potential_subjects[0]}")
                
                result = fetch_wiki_summary(query)
                return f"According to Wikipedia... {result}", "IDLE"
            except (wikipedia.exceptions.PageError, wikipedia.exceptions.DisambiguationError):
                return f"Sorry, I could not find any results for {query} on Wikipedia.", "IDLE"
            except Exception as e:
                self.assistant.logger.error(f"Wikipedia skill error: {e}", exc_info=True)
                return "Wikipedia service is temporarily unavailable, please try again.", "IDLE"
