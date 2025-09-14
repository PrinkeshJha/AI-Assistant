import requests
from config import OPENWEATHER_API_KEY
from .base_skill import Skill

class WeatherSkill(Skill):
    def intents(self):
        return ["weather", "temperature", "forecast"]

    def handle(self, command, doc):
        location = next((ent.text for ent in doc.ents if ent.label_ == "GPE"), None)
        if not location and "in" in command:
            location = command.split("in")[-1].strip()

        if not location:
            return "I'm not sure which city you're asking about.", "IDLE"

        url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={OPENWEATHER_API_KEY}&units=metric"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            temp = data['main']['temp']
            desc = data['weather'][0]['description']
            return f"The current weather in {location} is {desc} with a temperature of {temp} degrees Celsius.", "IDLE"
        except requests.exceptions.HTTPError:
            return f"Sorry, I couldn't find the weather for {location}.", "IDLE"
        except Exception as e:
            print(f"Weather skill error: {e}")
            return "Sorry, an error occurred while fetching the weather.", "IDLE"