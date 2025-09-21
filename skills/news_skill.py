# skills/news_skill.py
import requests
from config import NEWS_API_KEY
from .base_skill import Skill

class NewsSkill(Skill):
    def intents(self):
        return ["news", "headlines"]

    def handle(self, command, doc):
        url = f"https://gnews.io/api/v4/top-headlines?language=en&country=in&category=general&apikey={NEWS_API_KEY}"
        # self.assistant.speak("Fetching the latest news headlines...")

        try:
            response = requests.get(url)
            response.raise_for_status()
            
            data = response.json()
            articles = data.get('articles', [])
            if not articles:
                return "I couldn't find any news articles at the moment.", "IDLE"
            
            headlines = "Here are the top headlines...<br><br>" + "<br>".join([article['title'] for article in articles[:5]])
            return headlines, "IDLE"
        except Exception as e:
            print(f"News skill error: {e}")
            return "Sorry, I couldn't connect to the news service right now.", "IDLE"