# 🎙️ Jarvis — AI Voice Assistant

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-SocketIO-000000?logo=flask&logoColor=white)
![Groq](https://img.shields.io/badge/LLM-Groq_Llama_3.3-F55036?logo=meta&logoColor=white)
![FAISS](https://img.shields.io/badge/Vector_DB-FAISS-0467DF?logo=meta&logoColor=white)
![SentenceTransformers](https://img.shields.io/badge/NLU-Sentence_Transformers-FF6F00)
![Redis](https://img.shields.io/badge/Memory-Redis-DC382D?logo=redis&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-24_Passed-10B981?logo=pytest&logoColor=white)

A production-grade, **multi-user AI voice & text assistant** built from scratch — featuring semantic intent classification, an LLM conversational fallback, a document QA (RAG) pipeline, real-time WebSocket communication, and a premium glassmorphism UI.

> **Built to demonstrate**: Full-stack AI systems engineering — NLU pipelines, vector search, LLM integration, session-safe concurrency, resilient API orchestration, and modern web design.

---

## ✨ Key Highlights

| Capability | How It Works |
|---|---|
| 🗣️ **Voice + Text Input** | Browser Web Speech API → Socket.IO → Flask backend |
| 🧠 **Semantic Intent Classification** | `all-MiniLM-L6-v2` sentence embeddings with calibrated cosine similarity thresholds |
| 🤖 **LLM Conversational Fallback** | Groq Cloud `llama-3.3-70b-versatile` with multi-turn context + conversation summarization |
| 📄 **RAG Document QA** | Upload PDF/TXT/DOCX → chunking → FAISS vector index → grounded LLM answers |
| 🔌 **Pluggable Skill System** | Auto-discovered at startup — add one JSON + one Python file to extend |
| 👥 **Multi-User Session Isolation** | Thread-safe Redis-backed contexts with automatic in-memory fallback |
| 🔁 **Conversational Context** | Pronoun resolution, ellipsis merging, and multi-turn memory with auto-summarization |
| 📊 **Observability** | Every query logged to SQLite — intent, confidence, latency, token usage, RAG flag |
| 🛡️ **Resilience** | 5s timeouts, 3× exponential retries (Tenacity), 5-min TTL response caching |
| 🎨 **Premium UI** | Glassmorphism design, animated orb, particle effects, responsive layout |

---

## 🏗️ Architecture

```
                        ┌──────────────────────────────────┐
                        │        Browser (Client)          │
                        │  Web Speech API  ·  Text Input   │
                        │  File Upload  ·  TTS Playback    │
                        └──────────┬───────────────────────┘
                                   │ Socket.IO (bidirectional)
                                   ▼
                        ┌──────────────────────────────────┐
                        │    Flask-SocketIO  (app.py)       │
                        │    Thread-pool concurrency        │
                        │    Session ID → isolated context  │
                        └──────────┬───────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Assistant Core (assistant.py)                    │
│                                                                     │
│  1. Context Resolution ──► Pronoun + Ellipsis/Fragment Merging      │
│  2. Intent Classification ──► Embedding Cosine Similarity (≥0.65)   │
│  3. Dispatch ──► Skill Engine  |  Clarification  |  LLM Fallback   │
│  4. Memory ──► History tracking + auto-summarization (≥5 turns)     │
│  5. Analytics ──► SQLite metric logging per query                   │
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

### How a Query Flows

1. **Input** — User speaks or types a command. The browser captures it and sends it to the backend via Socket.IO.
2. **Context Resolution** — The context manager resolves pronouns (*"What about it?"* → *"What about Paris?"*) and merges ellipsis fragments (*"and there?"* → *"weather in Munich"*) using spaCy NER and conversation history.
3. **Intent Classification** — The query is encoded with `all-MiniLM-L6-v2` and compared against precomputed intent embeddings using cosine similarity. A calibration layer maps raw scores to actionable confidence values.
4. **Routing Decision**:
   - **≥ 0.65 confidence** → dispatched to the matching skill
   - **< 0.65 with 2+ plausible intents (≥ 0.3)** → clarification prompt with clickable suggestions
   - **< 0.65 with ≤ 1 plausible intent** → LLM fallback with full conversational context
5. **Response** — The result is emitted back to the client via Socket.IO, rendered in the chat UI, and optionally spoken aloud via browser TTS (voice-triggered queries only).
6. **Logging** — Every interaction is recorded to SQLite with intent, confidence, skill, status, LLM latency, token count, and RAG flag.

---

## 📂 Project Structure

```
AI-Assistant/
├── app.py                    # Flask-SocketIO server, file upload & document management routes
├── assistant.py              # Core assistant logic — classification, dispatch, context, summarization
├── config.py                 # API keys, wake word, assistant name, feature toggles
├── session_context.py        # Thread-safe session context accessor (Redis-backed)
├── requirements.txt          # Python dependencies
│
├── classifier/
│   └── embedding_classifier.py   # Sentence-transformer NLU with calibrated confidence scoring
│
├── context/
│   └── context_manager.py        # Pronoun resolution, ellipsis merging, entity tracking, history
│
├── services/
│   ├── llm_service.py            # Groq LLM client — ask(), summarize_history() with retries
│   ├── weather_service.py        # OpenWeatherMap API with TTL cache + retries
│   ├── news_service.py           # GNews API with TTL cache + retries
│   └── wiki_service.py           # Wikipedia API with TTL cache + retries
│
├── skills/
│   ├── base_skill.py             # Abstract base class for all skills
│   ├── weather_skill.py          # Weather forecast with optional LLM rephrasing
│   ├── news_skill.py             # Top headlines
│   ├── wiki_skill.py             # Wikipedia search + Google/YouTube shortcuts
│   ├── rag_skill.py              # Document QA — retrieves chunks, sends to LLM
│   ├── time_skill.py             # Time, date, day of week
│   ├── system_skill.py           # Battery status, open Notepad/Calculator
│   ├── fun_skill.py              # Programming jokes (pyjokes)
│   ├── help_skill.py             # Dynamic command listing
│   └── control_skill.py          # Exit / goodbye handling
│
├── rag/
│   ├── chunking.py               # Word-based overlapping text splitter
│   ├── embeddings.py             # Shared sentence-transformer encoder
│   ├── vector_store.py           # Session-scoped FAISS index with disk persistence
│   └── retriever.py              # Top-k similarity search over session index
│
├── memory/
│   └── redis_store.py            # Redis client with auto-persisting RedisDict + local fallback
│
├── analytics/
│   └── metrics.py                # SQLite logger — intent distribution, fallback rate, latency
│
├── intents/                      # Intent definition JSONs (one per skill)
│   ├── weather.json              # 16 example phrases for WeatherSkill
│   ├── news.json                 # 10 example phrases for NewsSkill
│   ├── wiki.json                 # 20 example phrases for WikiSkill
│   ├── rag.json                  # 10 example phrases for RAGSkill
│   ├── time.json, system.json, jokes.json, help.json, control.json
│
├── templates/
│   └── jarvis_ui.html            # Main HTML — glassmorphism UI with particle canvas
│
├── static/
│   ├── js/app.js                 # Entry point — initializes store, socket, components
│   ├── api/socket.js             # Socket.IO client wrapper with reconnection
│   ├── api/rest.js               # XHR file upload + document CRUD client
│   ├── state/store.js            # Reactive state store with subscriber pattern
│   ├── components/chat-window.js       # Incremental chat renderer with source badges
│   ├── components/voice-control.js     # Speech recognition + TTS + orb state management
│   ├── components/upload-drawer.js     # Drag-and-drop file upload with progress tracking
│   ├── components/connection-indicator.js  # Live connection status badge
│   └── styles/jarvis.css         # Full design system — glassmorphism, orb, animations
│
├── tests/                        # 24 unit tests (all mocked, offline-safe)
│   ├── test_dispatch.py          # Intent-to-skill routing verification
│   ├── test_context.py           # Session isolation + pronoun resolution
│   ├── test_llm.py               # LLM calls, summarization, fallback, metrics
│   ├── test_phase2.py            # Semantic classification, clarification, ellipsis, memory
│   ├── test_rag.py               # Chunking, FAISS indexing, upload route, document CRUD
│   ├── test_weather.py           # Caching, retry recovery, LLM skill collaboration
│   └── test_news.py              # News caching
│
└── logs/
    ├── assistant.log             # Runtime execution log
    └── metrics.db                # SQLite analytics database
```

---

## ⚡ Concurrency & Session Model

Jarvis supports **multiple concurrent users** without context cross-talk:

- **Thread-Based Concurrency** — Flask-SocketIO runs with `async_mode="threading"`, handling each client in its own thread.
- **Redis-Backed Persistence** — Session memory (entities, history, summaries) is stored in Redis via a custom `RedisDict` that auto-serializes on every mutation (`__setitem__`, `clear`, `pop`, etc.).
- **Silent Local Fallback** — If Redis is unavailable at startup, Jarvis seamlessly falls back to an in-memory dictionary with no user-facing impact.
- **Conversation Summarization** — When turn history reaches 5 entries, the LLM automatically compresses it into a bullet-point summary, keeping context windows small while preserving conversational continuity.

---

## 🛡️ Resilience & Reliability

| Mechanism | Implementation |
|---|---|
| **Timeouts** | Every external API call enforces a strict 5-second timeout |
| **Retries** | `@retry` decorator (Tenacity) — 3 attempts with exponential backoff |
| **Caching** | `TTLCache` (300s TTL) per resource type — weather, news, Wikipedia |
| **Graceful Degradation** | Skills catch exceptions and return friendly messages; tracebacks go to `logs/assistant.log` |
| **LLM Safety Net** | If classification confidence is too low and no skills match, the query is routed to the LLM with full conversational context |

---

## 🚀 Setup & Installation

### Prerequisites
- Python 3.8+
- Redis Server *(optional — for persistent session memory)*
- Working microphone *(for voice recognition in the browser)*

### Quick Start

```bash
# 1. Clone
git clone https://github.com/PrinkeshJha/AI-Assistant.git
cd AI-Assistant

# 2. Virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Download spaCy model
python -m spacy download en_core_web_sm

# 5. Configure
cp example.config.py config.py
cp .env.example .env
# Edit .env with your API keys:
#   NEWS_API_KEY, OPENWEATHER_API_KEY, PICOVOICE_ACCESS_KEY, GROQ_API_KEY

# 6. Launch
python app.py
```

Open **http://127.0.0.1:5000** → allow microphone access → click the orb or type a command.

### API Keys Required

| Key | Provider | Purpose |
|---|---|---|
| `NEWS_API_KEY` | [GNews](https://gnews.io/) | Top headlines |
| `OPENWEATHER_API_KEY` | [OpenWeatherMap](https://openweathermap.org/) | Weather data |
| `PICOVOICE_ACCESS_KEY` | [Picovoice](https://console.picovoice.ai/) | Wake word detection |
| `GROQ_API_KEY` | [Groq](https://console.groq.com/) | LLM fallback & RAG answers |

---

## 🔌 Extending Jarvis — Add a New Skill

Skills are **fully pluggable** — no core code changes needed. Just add two files:

**1. Create an intent file** (`intents/greet.json`):
```json
{
  "intent": "GreetSkill",
  "examples": [
    "hello", "hi there", "good morning", "hey jarvis"
  ]
}
```

**2. Create a skill module** (`skills/greet_skill.py`):
```python
from .base_skill import Skill

class GreetSkill(Skill):
    def intents(self) -> list[str]:
        return ["hello", "hi", "hey"]

    def handle(self, command: str, doc) -> tuple[str, str]:
        return "Hello, Sir. How can I assist you today?", "IDLE"
```

> **Important**: The class name (`GreetSkill`) must match the `"intent"` value in the JSON file.

Restart the server — the skill is automatically discovered and loaded.

---

## 📊 Analytics & Observability

Every query logs a structured record to `logs/metrics.db`:

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
| `is_rag_query` | INTEGER | `1` if document-grounded |

Helper functions available in `analytics/metrics.py`:
- `get_intent_distribution()` — query counts per intent
- `get_average_confidence()` — mean classification confidence
- `get_fallback_rate()` — fraction of LLM-routed queries
- `get_average_llm_latency()` — mean LLM response time
- `get_rag_query_count()` — total RAG queries

---

## ✅ Testing

```bash
.\venv\Scripts\pytest tests/ -v
```

**24 tests** covering:
- Intent-to-skill dispatch routing
- Session isolation & pronoun/ellipsis context resolution
- LLM fallback, summarization, and conversation memory
- Confidence threshold → clarification prompt flow
- FAISS RAG pipeline (chunking, indexing, retrieval, session isolation)
- File upload/delete REST endpoints with index rebuilding
- Weather/news service caching and retry recovery
- Skill execution error handling and graceful degradation

All external APIs are mocked — tests run fully offline.

---

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| **Language** | Python 3.8+ |
| **Backend** | Flask, Flask-SocketIO |
| **NLU** | Sentence Transformers (`all-MiniLM-L6-v2`), spaCy |
| **LLM** | Groq Cloud (`llama-3.3-70b-versatile`, `llama-3.1-8b-instant`) |
| **Vector DB** | FAISS (session-isolated, disk-persisted) |
| **Memory** | Redis (with local dict fallback) |
| **Analytics** | SQLite |
| **Frontend** | Vanilla JS (ES Modules), Web Speech API, CSS3 |
| **Resilience** | Tenacity (retries), cachetools (TTL cache) |
| **Testing** | pytest, unittest.mock |

---

<p align="center"><em>Designed and built by <a href="https://github.com/PrinkeshJha">Prinkesh Jha</a></em></p>
