# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- API Keys ---
# Get from https://gnews.io/
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "")
# Get from https://openweathermap.org/
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")
# Get from https://console.picovoice.ai/
PICOVOICE_ACCESS_KEY = os.environ.get("PICOVOICE_ACCESS_KEY", "")
# Get from https://console.groq.com/
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# Toggle to naturally phrase structured skill outputs (e.g. weather) via LLM
LLM_FORMAT_SKILLS = False

# --- Assistant Configuration ---
WAKE_WORD = "jarvis"
ASSISTANT_NAME = "Jarvis"

# To find your microphone's index, run the 'list_mics.py' script from the setup instructions.
# For most systems, leaving it as None will use the default microphone.
MICROPHONE_INDEX = 2

# --- SaaS Database & Auth Configurations ---
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "jarvis-super-secret-key-123!")
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'logs', 'jarvis.db')}")
# Ensure the logs directory exists for SQLite
os.makedirs(os.path.join(BASE_DIR, "logs"), exist_ok=True)
