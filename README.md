# 🎙️ Jarvis - A Multi-User AI Voice Assistant  

Jarvis is a modern, concurrent **AI voice assistant** featuring a web-based user interface, modular skills, and thread-safe session tracking.  

---

## 🏗️ System Architecture  

The system operates concurrently using the following execution pipeline:

```
[ Browser Web Speech API ] 
         │  (Voice Input)
         ▼
[ Client-side JS Recognition ]
         │  (Parsed Text Request)
         ▼  (Socket.IO - Multi-User Concurrent Rooms)
[ Flask-SocketIO Backend (app.py) ]
         │  (Session Isolation: request.sid Context Local)
         ▼
[ Assistant Logic (assistant.py) ] ── (Regex Pronoun Resolution & spaCy NER)
         │  
         ▼  (Pluggable Skill Dispatching)
[ skills/ ] ─────────────► [ services/ ]
  - weather_skill.py        - weather_service.py (API call, timeout=5, retries, caching)
  - news_skill.py           - news_service.py    (API call, timeout=5, retries, caching)
  - wiki_skill.py           - wiki_service.py    (API call, timeout=5, retries, caching)
```

1. **Frontend (Browser)**: Captures voice input, processes speech recognition locally, and establishes a bidirectional Socket.IO connection.
2. **Backend Concurrency (Flask-SocketIO)**: Routes concurrent client rooms via thread pools, assigning unique contexts mapped to socket session IDs (`request.sid`).
3. **NLP Processing (spaCy)**: Performs cased Named Entity Recognition (NER) and resolves pronoun references (e.g., "Paris" -> "its weather").
4. **Resilient Service Layer**: Fetches data from external REST APIs using retries, client timeouts, and cache layers.

---

## ⚡ Concurrency & Session Model  

To support multiple concurrent users without context cross-talk (e.g., User B's queries resolving against User A's last subject), Jarvis implements:
* **Thread-Based Concurrency**: Runs with `async_mode="threading"` inside Flask-SocketIO.
* **Session Context Manager**: The `session_context.py` manager handles client-specific data. Contexts are isolated using the client's `request.sid` session token.
* **Leak Prevention**: Mapped socket sessions are initialized on client `connect` events and deleted from the global memory store on `disconnect`.

---

## 🛡️ Reliability & Resilience Features  

* **API Client Timeouts**: Every service method is locked to a strict `timeout=5` seconds to prevent slow external API calls from blocking worker threads. For third-party packages (e.g. `wikipedia`), underlying requests are monkeypatched at initialization to guarantee the timeout.
* **Tenacity Retries**: Service calls are wrapped with a `@retry` decorator from the `tenacity` library, attempting recovery 3 times using exponential backoff before bubbling up failures.
* **Resource Caching**: Leverages `cachetools.TTLCache` (TTL: 300s) per resource type (weather, news headlines, Wikipedia summaries) to eliminate redundant external roundtrips.
* **Graceful Fallbacks**: Skill modules wrap execution with try-except blocks. If a service becomes completely unreachable, Jarvis responds with a friendly message (e.g., *"Weather service is temporarily unavailable, please try again."*) and writes the traceback details to `logs/assistant.log`.
* **Latency Logging**: Invocations are timed, and execution durations (in milliseconds) are recorded in `logs/assistant.log` to track bottleneck areas.

---

## 🚀 Setup & Installation  

### 1️⃣ Prerequisites  
- Python 3.8 or higher.  
- Working microphone (for voice recognition in the browser).  

### 2️⃣ Clone the Repository  
```bash
git clone https://github.com/PrinkeshJha/AI-Assistant.git
cd AI-Assistant
```

### 3️⃣ Create a Virtual Environment  
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 4️⃣ Install Dependencies  
```bash
pip install -r requirements.txt
```

### 5️⃣ Download spaCy Model  
```bash
python -m spacy download en_core_web_sm
```

### 6️⃣ Configure Secrets (.env)  
API keys must be stored in a `.env` file at the root of the project (this file is ignored by git).  
1. Copy the example environment template:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` and fill in your API credentials:
   ```env
   NEWS_API_KEY=your_gnews_api_key_here
   OPENWEATHER_API_KEY=your_openweathermap_key_here
   PICOVOICE_ACCESS_KEY=your_picovoice_key_here
   ```

---

## ▶️ Running & Testing  

### Running Jarvis  
Start the Flask application server:  
```bash
python app.py
```
* Open **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your web browser.  
* Allow microphone access, click the central orb, and ask questions!

### Running the Test Suite  
Jarvis contains a complete suite of tests verifying session context isolation, routing, and caching behavior using mocks:  
```bash
pytest
```
All external APIs are mocked during unit testing to ensure they run offline.
