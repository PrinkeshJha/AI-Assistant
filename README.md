# 🎙️ Jarvis - Multi-User AI Voice Assistant with Semantic NLU

Jarvis is a modern, concurrent **AI voice assistant** featuring a web-based user interface, modular skill loading, semantic intent classification, persistent session isolation, and automated performance tracking.

---

## 🏗️ System Architecture

The assistant executes concurrently using the following pipeline:

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
[ Assistant Logic (assistant.py) ]
         │
         ├─► [ Context Manager (context/context_manager.py) ]
         │     (Pronoun Resolution & Ellipsis/Fragment Merging)
         │
         ├─► [ Embedding Classifier (classifier/embedding_classifier.py) ]
         │     (all-MiniLM-L6-v2 Semantic Similarity, Threshold: 0.65)
         │
         ├─► [ Analytics Logger (analytics/metrics.py) ]
         │     (Writes session, query, intent, confidence, status, latency to SQLite)
         │
         ├─► [ LLM Fallback (services/llm_service.py) ]
         │     (Groq Cloud llama-3.3-70b-versatile, timeout=5, Tenacity retries)
         │
         ├─► [ RAG Pipeline (rag/) ]
         │     (Word-based overlapping chunks, FAISS local indices per session)
         │
         ▼  (Pluggable Skill Dispatching)
[ skills/ ] ─────────────► [ services/ ]
  - weather_skill.py        - weather_service.py (API call, timeout=5, retries, caching)
  - news_skill.py           - news_service.py    (API call, timeout=5, retries, caching)
  - wiki_skill.py           - wiki_service.py    (API call, timeout=5, retries, caching)
  - rag_skill.py            - SessionVectorStore (FAISS local RAG querying)
```

1. **Frontend (Browser)**: Captures voice input, processes speech recognition locally, and establishes a bidirectional Socket.IO connection. Includes typed input and file upload options.
2. **Backend Concurrency (Flask-SocketIO)**: Routes concurrent client rooms via thread pools, assigning unique contexts mapped to socket session IDs (`request.sid`).
3. **Advanced Context Manager**: Intercepts queries, resolves pronoun references, and merges conversational fragments (ellipsis queries, e.g. "what about Paris?") against historical context.
4. **Semantic NLU (Sentence Transformers)**: Encodes queries using `all-MiniLM-L6-v2` and classifies them using cosine similarity against precomputed intent example vectors with a safety threshold of `0.65`.
5. **LLM Fallback (Groq)**: Below-threshold queries with no matching skills automatically route to Groq Cloud's hosted `llama-3.3-70b-versatile` API.
6. **RAG Pipeline (FAISS)**: Uploaded PDFs, TXTs, or DOCXs are parsed, split into overlapping word chunks, embedded via the shared `all-MiniLM-L6-v2` encoder, and saved to a session-isolated FAISS database.
7. **Conversational Memory Summarization**: When history reaches 5 turns, Groq automatically compresses it into a concise bullet-point summary stored in Redis, pruning raw logs.
8. **SQLite Metrics Tracking**: Logs query performance, intent distribution, fallback rate, RAG usage, and LLM call latency in `logs/metrics.db`.

---

## ⚡ Concurrency & Session Model

To support multiple concurrent users without context cross-talk (e.g., User B's queries resolving against User A's last subject), Jarvis implements:
* **Thread-Based Concurrency**: Runs with `async_mode="threading"` inside Flask-SocketIO.
* **Persistent Redis Store**: Session memory is backed by a local Redis daemon (port 6379) using `RedisStore`.
* **Automatic Silent Fallback**: If no Redis server is detected at startup, the assistant automatically and silently falls back to an in-memory dictionary.
* **Mutating Dict Wrapper**: Leverages a custom `RedisDict` which intercepts mutations (`__setitem__`, `__delitem__`, `clear`, etc.) and automatically serializes state updates back to Redis/fallback store instantly, keeping the codebase clean and signature-stable.

---

## 🛡️ Reliability & Resilience Features

* **API Client Timeouts**: Every service method is locked to a strict `timeout=5` seconds to prevent slow external API calls from blocking worker threads.
* **Tenacity Retries**: Service calls are wrapped with a `@retry` decorator from the `tenacity` library, attempting recovery 3 times using exponential backoff before bubbling up failures.
* **Resource Caching**: Leverages `cachetools.TTLCache` (TTL: 300s) per resource type (weather, news headlines, Wikipedia summaries) to eliminate redundant external roundtrips.
* **Graceful Fallbacks**: Skill modules wrap execution with try-except blocks. If a service becomes completely unreachable, Jarvis responds with a friendly message and writes the traceback details to `logs/assistant.log`.

---

## 🚀 Setup & Installation

### 1️⃣ Prerequisites
- Python 3.8 or higher.
- Redis Server (Optional, for persistent session memory).
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

### 6️⃣ Initialize Configurations
The project requires a local configuration and environment variables for external APIs.
1. **Copy the example configuration files**:
   ```bash
   cp example.config.py config.py
   cp .env.example .env
   ```
2. **Configure Local Variables (`config.py`)**:
   Adjust configurations such as `WAKE_WORD` or `MICROPHONE_INDEX`. Toggle `LLM_FORMAT_SKILLS` to `True` to route weather and skill data through the LLM for natural-language phrasing.
3. **Configure Environment Secrets (`.env`)**:
   Open `.env` and fill in your API credentials:
   ```env
   NEWS_API_KEY=your_gnews_api_key_here
   OPENWEATHER_API_KEY=your_openweathermap_key_here
   PICOVOICE_ACCESS_KEY=your_picovoice_key_here
   GROQ_API_KEY=your_groq_cloud_api_key_here
   ```

---

## 🛠️ Developer Guide: Extending Jarvis

### How to Add a New Skill
Skills in Jarvis are completely pluggable and loaded dynamically at startup.

1. **Create an Intent File**:
   Add a JSON file inside [intents/](file:///e:/AI-Assistant/intents) (e.g., `greet.json`):
   ```json
   {
     "intent": "GreetSkill",
     "examples": [
       "hello",
       "hi there",
       "good morning",
       "hey jarvis"
     ]
   }
   ```
2. **Create the Skill Module**:
   Add a Python file inside [skills/](file:///e:/AI-Assistant/skills) (e.g., `greet_skill.py`):
   ```python
   from .base_skill import Skill

   class GreetSkill(Skill):
       def intents(self) -> list[str]:
           return ["hello", "hi", "hey"]

       def handle(self, command: str, doc) -> tuple[str, str]:
           response = "Hello, Sir. How can I assist you today?"
           return response, "IDLE"
   ```
   *Note: The class name (`GreetSkill`) MUST match the `"intent"` name specified in your intent JSON file.*

---

## 📊 Analytics & Performance Tracking

Every command processed by Jarvis logs its execution metrics to a local SQLite database at `logs/metrics.db`.

### Database Schema (`command_metrics` table)
| Column Name | Type | Description |
|---|---|---|
| `id` | INTEGER (PK) | Auto-incrementing identifier |
| `session_id` | TEXT | Unique Socket.IO connection session identifier (`request.sid`) |
| `timestamp` | REAL | Epoch timestamp of command invocation |
| `query` | TEXT | Raw processed query string |
| `detected_intent` | TEXT | The identified intent classifier class name |
| `confidence` | REAL | Semantic classification score |
| `resolved_skill` | TEXT | Pluggable skill class executed (or "None" if fallback) |
| `success_status` | TEXT | Status outcome (`SUCCESS`, `CLARIFICATION`, `FALLBACK`, `ERROR`) |
| `llm_latency` | REAL | Time elapsed during LLM generation in seconds |
| `llm_tokens_used` | INTEGER | Token consumption returned by completions API |
| `is_rag_query` | INTEGER | Flag indicator (`0` or `1`) for document-grounded inquiries |

---

## ▶️ Running & Testing

### Running Jarvis
Start the Flask application server:
```bash
python app.py
```
* Open **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your web browser.
* Allow microphone access, click the central orb, and start talking!
* **Upload Notes**: Use the "Upload" button to load PDF, TXT, or DOCX documents to query your notes.

### Running the Test Suite
To verify the entire pipeline (including session contexts, semantic thresholds, retry recovery, context pronoun and ellipsis merging, local RAG pipelines, and SQLite metric logs):
```bash
.\venv\Scripts\pytest
```
All external APIs are mocked during unit testing to guarantee offline-first execution.
