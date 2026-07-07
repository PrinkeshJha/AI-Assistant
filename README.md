# 🎙️ Jarvis AI — Voice & Knowledge Assistant

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-SocketIO-000000?logo=flask&logoColor=white)
![Groq](https://img.shields.io/badge/LLM-Groq_Llama_3.3-F55036?logo=meta&logoColor=white)
![FAISS](https://img.shields.io/badge/Vector_DB-FAISS-0467DF?logo=meta&logoColor=white)
![SentenceTransformers](https://img.shields.io/badge/NLU-Sentence_Transformers-FF6F00)
![Redis](https://img.shields.io/badge/Memory-Redis-DC382D?logo=redis&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-24_Passed-10B981?logo=pytest&logoColor=white)

Jarvis is a full-stack AI voice and text assistant I built from the ground up — not just a wrapper around an LLM, but a proper system with semantic intent classification, document-grounded Q&A (RAG), real-time WebSocket communication, and multi-user session handling that actually works under concurrency.

I built this to go deep on the parts of AI systems engineering that don't show up in tutorials: NLU pipelines, vector search, resilient API orchestration, and session-safe architecture — wrapped in a UI that doesn't look like a class project.

---

## Why This Project Exists

Most "AI assistant" demos are a single API call to an LLM with a chat box glued on top. Jarvis is different — it tries to behave like a real assistant:

- It **understands intent** before deciding whether to run a skill, ask for clarification, or hand things off to an LLM.
- It **remembers context** across turns — so "what about tomorrow?" actually resolves to the right follow-up question.
- It **grounds answers in your documents** when you upload a PDF or DOCX, instead of hallucinating.
- It **stays isolated per user** — two people talking to Jarvis at once never see each other's context.
- It **degrades gracefully** when an external API times out or Redis isn't running, instead of crashing.

---

## ✨ Key Highlights

| Capability | How It Works |
|---|---|
| 🗣️ Voice + Text Input | Browser Web Speech API → Socket.IO → Flask backend |
| 🧠 Semantic Intent Classification | `all-MiniLM-L6-v2` embeddings with calibrated cosine similarity thresholds |
| 🤖 LLM Conversational Fallback | Groq Cloud `llama-3.3-70b-versatile` with multi-turn context + summarization |
| 📄 RAG Document Q&A | Upload PDF/TXT/DOCX → chunk → FAISS index → grounded LLM answers |
| 🔌 Pluggable Skill System | Auto-discovered at startup — add one JSON + one Python file to extend |
| 👥 Multi-User Session Isolation | Thread-safe, Redis-backed contexts with automatic in-memory fallback |
| 🔁 Conversational Context | Pronoun resolution, ellipsis merging, multi-turn memory with auto-summarization |
| 📊 Observability | Every query logged to SQLite — intent, confidence, latency, tokens, RAG flag |
| 🛡️ Resilience | 5s timeouts, 3× exponential retries (Tenacity), 5-minute TTL caching |
| 🎨 Premium UI | Glassmorphism design, animated orb, particle effects, responsive layout |

---

## 🏗️ Architecture

```
                        ┌──────────────────────────────────┐
                        │        Browser (Client)          │
                        │  Web Speech API  ·  Text Input   │
                        │  File Upload  ·  TTS Playback     │
                        └──────────┬───────────────────────┘
                                   │ Socket.IO (bidirectional)
                                   ▼
                        ┌──────────────────────────────────┐
                        │    Flask-SocketIO  (app.py)       │
                        │    Thread-pool concurrency         │
                        │    Session ID → isolated context   │
                        └──────────┬───────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Assistant Core (assistant.py)                    │
│                                                                       │
│  1. Context Resolution  → Pronoun + ellipsis/fragment merging        │
│  2. Intent Classification → Embedding cosine similarity (≥ 0.65)     │
│  3. Dispatch             → Skill Engine | Clarification | LLM Fallback│
│  4. Memory               → History tracking + auto-summarization      │
│  5. Analytics            → SQLite metric logging per query           │
└──────┬──────────────┬──────────────┬──────────────┬─────────────────┘
       │              │              │              │
       ▼              ▼              ▼              ▼
  ┌─────────┐   ┌──────────┐  ┌──────────┐   ┌──────────┐
  │ Skills   │   │ Services │  │   RAG    │   │  Memory  │
  │ weather  │   │ weather  │  │ chunking │   │  Redis   │
  │ news     │   │ news     │  │ embedder │   │  Store   │
  │ wiki     │   │ wiki     │  │ FAISS    │   │ (+ local │
  │ time     │   │ llm      │  │ retriever│   │ fallback)│
  │ system   │   └──────────┘  └──────────┘   └──────────┘
  │ fun/joke │
  │ help     │
  │ rag      │
  │ control  │
  └──────────┘
```

### How a Query Actually Flows

1. **Input** — You speak or type a command. The browser captures it and sends it to the backend over Socket.IO.
2. **Context Resolution** — The context manager resolves pronouns (*"What about it?"* → *"What about Paris?"*) and merges ellipsis fragments (*"and there?"* → *"weather in Munich"*) using spaCy NER plus conversation history.
3. **Intent Classification** — The query is encoded with `all-MiniLM-L6-v2` and compared against precomputed intent embeddings via cosine similarity. A calibration layer converts raw scores into usable confidence values.
4. **Routing Decision**:
   - **≥ 0.65 confidence** → dispatched straight to the matching skill
   - **< 0.65, with 2+ plausible intents (≥ 0.3)** → a clarification prompt with clickable suggestions
   - **< 0.65, with ≤ 1 plausible intent** → falls back to the LLM with full conversational context
5. **Response** — The reply goes back to the client over Socket.IO, renders in the chat UI, and — for voice-triggered queries — gets spoken aloud via browser TTS.
6. **Logging** — Every interaction is recorded to SQLite with intent, confidence, skill, status, LLM latency, token count, and RAG flag.

---

## 📂 Project Structure

```
AI-Assistant/
├── app.py                    # Flask-SocketIO server, file upload & document routes
├── assistant.py               # Core logic — classification, dispatch, context, summarization
├── config.py                  # API keys, wake word, assistant name, feature toggles
├── session_context.py         # Thread-safe session context accessor (Redis-backed)
├── requirements.txt            # Python dependencies
│
├── classifier/
│   └── embedding_classifier.py    # Sentence-transformer NLU with calibrated confidence
│
├── context/
│   └── context_manager.py         # Pronoun resolution, ellipsis merging, entity tracking
│
├── services/
│   ├── llm_service.py              # Groq LLM client — ask(), summarize_history() with retries
│   ├── weather_service.py          # OpenWeatherMap API with TTL cache + retries
│   ├── news_service.py             # GNews API with TTL cache + retries
│   └── wiki_service.py             # Wikipedia API with TTL cache + retries
│
├── skills/
│   ├── base_skill.py               # Abstract base class for all skills
│   ├── weather_skill.py            # Weather forecast with optional LLM rephrasing
│   ├── news_skill.py               # Top headlines
│   ├── wiki_skill.py                # Wikipedia search + Google/YouTube shortcuts
│   ├── rag_skill.py                 # Document QA — retrieves chunks, sends to LLM
│   ├── time_skill.py                # Time, date, day of week
│   ├── system_skill.py              # Battery status, open Notepad/Calculator
│   ├── fun_skill.py                 # Programming jokes (pyjokes)
│   ├── help_skill.py                # Dynamic command listing
│   └── control_skill.py             # Exit / goodbye handling
│
├── rag/
│   ├── chunking.py                   # Word-based overlapping text splitter
│   ├── embeddings.py                 # Shared sentence-transformer encoder
│   ├── vector_store.py               # Session-scoped FAISS index with disk persistence
│   └── retriever.py                  # Top-k similarity search over session index
│
├── memory/
│   └── redis_store.py                # Redis client with auto-persisting RedisDict + local fallback
│
├── analytics/
│   └── metrics.py                     # SQLite logger — intent distribution, fallback rate, latency
│
├── intents/                           # Intent definition JSONs (one per skill)
│   ├── weather.json                    # 16 example phrases for WeatherSkill
│   ├── news.json                       # 10 example phrases for NewsSkill
│   ├── wiki.json                       # 20 example phrases for WikiSkill
│   ├── rag.json                        # 10 example phrases for RAGSkill
│   └── time.json, system.json, jokes.json, help.json, control.json
│
├── templates/
│   └── jarvis_ui.html                  # Main HTML — glassmorphism UI with particle canvas
│
├── static/
│   ├── js/app.js                        # Entry point — initializes store, socket, components
│   ├── api/socket.js                    # Socket.IO client wrapper with reconnection
│   ├── api/rest.js                      # XHR file upload + document CRUD client
│   ├── state/store.js                   # Reactive state store with subscriber pattern
│   ├── components/chat-window.js        # Incremental chat renderer with source badges
│   ├── components/voice-control.js      # Speech recognition + TTS + orb state management
│   ├── components/upload-drawer.js      # Drag-and-drop file upload with progress tracking
│   ├── components/connection-indicator.js  # Live connection status badge
│   └── styles/jarvis.css                 # Full design system — glassmorphism, orb, animations
│
├── tests/                               # 24 unit tests, all mocked and offline-safe
│   ├── test_dispatch.py                  # Intent-to-skill routing verification
│   ├── test_context.py                   # Session isolation + pronoun resolution
│   ├── test_llm.py                        # LLM calls, summarization, fallback, metrics
│   ├── test_phase2.py                     # Semantic classification, clarification, ellipsis, memory
│   ├── test_rag.py                        # Chunking, FAISS indexing, upload route, document CRUD
│   ├── test_weather.py                    # Caching, retry recovery, LLM skill collaboration
│   └── test_news.py                       # News caching
│
└── logs/
    ├── assistant.log                       # Runtime execution log
    └── metrics.db                           # SQLite analytics database
```

---

## ⚡ Concurrency & Session Model

Jarvis is built to handle **multiple people talking to it at once**, without their conversations bleeding into each other:

- **Thread-based concurrency** — Flask-SocketIO runs with `async_mode="threading"`, so every client gets its own thread.
- **Redis-backed persistence** — Session memory (entities, history, summaries) lives in Redis through a custom `RedisDict` that auto-serializes on every mutation (`__setitem__`, `clear`, `pop`, etc.).
- **Silent local fallback** — If Redis isn't running when Jarvis starts, it quietly falls back to an in-memory dictionary. No errors, no user-facing impact.
- **Conversation summarization** — Once a session's turn history hits 5 entries, the LLM compresses it into a bullet-point summary, keeping the context window small without losing the thread of the conversation.

---

## 🛡️ Resilience & Reliability

Real assistants have to survive flaky networks and slow third-party APIs. Jarvis handles that with:

| Mechanism | Implementation |
|---|---|
| Timeouts | Every external API call enforces a strict 5-second timeout |
| Retries | `@retry` decorator (Tenacity) — 3 attempts with exponential backoff |
| Caching | `TTLCache` (300s TTL) per resource type — weather, news, Wikipedia |
| Graceful Degradation | Skills catch exceptions and return friendly messages; tracebacks go to `logs/assistant.log` |
| LLM Safety Net | If classification confidence is too low and no skill matches, the query goes to the LLM with full conversational context |

---

## 🚀 Setup & Installation

### Prerequisites
- Python 3.8+
- Redis Server *(optional — enables persistent session memory)*
- A working microphone *(for voice recognition in the browser)*

### Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/PrinkeshJha/AI-Assistant.git
cd AI-Assistant

# 2. Set up a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Download the spaCy model
python -m spacy download en_core_web_sm

# 5. Configure your environment
cp example.config.py config.py
cp .env.example .env
# Edit .env with your own API keys:
#   NEWS_API_KEY, OPENWEATHER_API_KEY, PICOVOICE_ACCESS_KEY, GROQ_API_KEY

# 6. Launch
python app.py
```

Then open **http://127.0.0.1:5000**, allow microphone access, and click the orb — or just start typing.

### API Keys You'll Need

| Key | Provider | Purpose |
|---|---|---|
| `NEWS_API_KEY` | [GNews](https://gnews.io/) | Top headlines |
| `OPENWEATHER_API_KEY` | [OpenWeatherMap](https://openweathermap.org/) | Weather data |
| `PICOVOICE_ACCESS_KEY` | [Picovoice](https://console.picovoice.ai/) | Wake word detection |
| `GROQ_API_KEY` | [Groq](https://console.groq.com/) | LLM fallback & RAG answers |

---

## 🔌 Extending Jarvis — Adding a New Skill

Skills are fully pluggable — you don't touch any core code. Just drop in two files:

**1. Add an intent file** (`intents/greet.json`):
```json
{
  "intent": "GreetSkill",
  "examples": [
    "hello", "hi there", "good morning", "hey jarvis"
  ]
}
```

**2. Add a skill module** (`skills/greet_skill.py`):
```python
from .base_skill import Skill

class GreetSkill(Skill):
    def intents(self) -> list[str]:
        return ["hello", "hi", "hey"]

    def handle(self, command: str, doc) -> tuple[str, str]:
        return "Hello, Sir. How can I assist you today?", "IDLE"
```

> **Note:** the class name (`GreetSkill`) has to match the `"intent"` value in the JSON file exactly.

Restart the server and the new skill is picked up automatically — no registration step needed.

---

## 📊 Analytics & Observability

Every single query gets logged as a structured record in `logs/metrics.db`:

| Column | Type | Description |
|---|---|---|
| `session_id` | TEXT | Socket.IO session identifier |
| `timestamp` | REAL | Epoch time of the query |
| `query` | TEXT | Processed query string |
| `detected_intent` | TEXT | Classified intent name |
| `confidence` | REAL | Semantic similarity score |
| `resolved_skill` | TEXT | Skill that handled the query |
| `success_status` | TEXT | `SUCCESS` · `CLARIFICATION` · `FALLBACK` · `ERROR` |
| `llm_latency` | REAL | LLM response time (seconds) |
| `llm_tokens_used` | INTEGER | Token consumption |
| `is_rag_query` | INTEGER | `1` if the answer was document-grounded |

Helper functions in `analytics/metrics.py` make this easy to query:
- `get_intent_distribution()` — query counts per intent
- `get_average_confidence()` — mean classification confidence
- `get_fallback_rate()` — fraction of queries routed to the LLM
- `get_average_llm_latency()` — mean LLM response time
- `get_rag_query_count()` — total document-grounded queries

---

## ✅ Testing

```bash
.\venv\Scripts\pytest tests/ -v
```

**24 tests**, covering:
- Intent-to-skill dispatch routing
- Session isolation and pronoun/ellipsis context resolution
- LLM fallback, summarization, and conversation memory
- Confidence threshold → clarification prompt flow
- The full FAISS RAG pipeline — chunking, indexing, retrieval, session isolation
- File upload/delete REST endpoints with index rebuilding
- Weather/news service caching and retry recovery
- Skill execution error handling and graceful degradation

Every external API is mocked, so the full suite runs offline.

---

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.8+ |
| Backend | Flask, Flask-SocketIO |
| NLU | Sentence Transformers (`all-MiniLM-L6-v2`), spaCy |
| LLM | Groq Cloud (`llama-3.3-70b-versatile`, `llama-3.1-8b-instant`) |
| Vector DB | FAISS (session-isolated, disk-persisted) |
| Memory | Redis (with local dict fallback) |
| Analytics | SQLite |
| Frontend | Vanilla JS (ES Modules), Web Speech API, CSS3 |
| Resilience | Tenacity (retries), cachetools (TTL cache) |
| Testing | pytest, unittest.mock |

---

<p align="center"><em>Designed and built by <a href="[def]">Prinkesh Jha</a></em></p>

[def]: ttps://github.com/PrinkeshJh