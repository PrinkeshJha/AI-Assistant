# skills/news_skill.py
from .base_skill import Skill
from services.news_service import fetch_news

class NewsSkill(Skill):
    def intents(self):
        return ["news", "headlines"]

    def handle(self, command, doc):
        try:
            articles = fetch_news()
            if not articles:
                return "I couldn't find any news articles at the moment.", "IDLE"
            
            headlines = "Here are the top headlines...<br><br>" + "<br>".join([article['title'] for article in articles[:5]])
            return headlines, "IDLE"
        except Exception as e:
            self.assistant.logger.error(f"News skill error: {e}", exc_info=True)
            return "News service is temporarily unavailable, please try again.", "IDLE"