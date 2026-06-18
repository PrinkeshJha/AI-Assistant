from .base_skill import Skill
from services.weather_service import fetch_weather
import requests

class WeatherSkill(Skill):
    def intents(self):
        return ["weather", "temperature", "forecast"]

    def handle(self, command, doc):
        location = next((ent.text for ent in doc.ents if ent.label_ == "GPE"), None)
        if not location and "in" in command:
            location = command.split("in")[-1].strip()

        if not location:
            return "I'm not sure which city you're asking about.", "IDLE"

        try:
            temp, desc = fetch_weather(location)
            return f"The current weather in {location} is {desc} with a temperature of {temp} degrees Celsius.", "IDLE"
        except requests.exceptions.HTTPError:
            return f"Sorry, I couldn't find the weather for {location}.", "IDLE"
        except Exception as e:
            self.assistant.logger.error(f"Weather skill error: {e}", exc_info=True)
            return "Weather service is temporarily unavailable, please try again.", "IDLE"