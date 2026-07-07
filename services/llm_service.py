import os
import time
import logging
from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential
from config import GROQ_API_KEY

logger = logging.getLogger("JarvisAssistant")

SYSTEM_PROMPT = (
    "You are Jarvis, a helpful, concise, and intelligent voice assistant. "
    "You are aware of your built-in skills: weather (forecast/temperature), "
    "news (top headlines), wiki (searching information), system (battery, notepad, calculator), "
    "time (time, date, day), and fun (jokes). "
    "For user queries that you answer, maintain a premium, professional, and slightly futuristic tone. "
    "Keep responses concise and conversational (ideal for text-to-speech rendering)."
)

_client = None

def get_client():
    global _client
    if _client is None:
        if not GROQ_API_KEY:
            logger.warning("GROQ_API_KEY is not set. LLM calls will fail.")
        _client = Groq(api_key=GROQ_API_KEY)
    return _client

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    reraise=True
)
def ask(prompt: str, context: list = None, summary: str = None) -> tuple[str, int, float]:
    """
    Sends a query to Groq chat completion API.
    Returns a tuple of (response_text, tokens_used, latency_seconds).
    """
    client = get_client()
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Inject conversational summary if available
    if summary:
        messages.append({
            "role": "system",
            "content": f"Summary of conversation so far: {summary}"
        })
        
    # Inject context turns
    if context:
        for turn in context:
            messages.append({"role": "user", "content": turn['query']})
            if 'response' in turn and turn['response']:
                messages.append({"role": "assistant", "content": turn['response']})
                
    # Add current prompt
    messages.append({"role": "user", "content": prompt})
    
    start_time = time.time()
    try:
        # Default model is llama-3.3-70b-versatile for high quality fallback answers.
        # Can toggle to llama-3.1-8b-instant if sub-100ms latency is strictly required.
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7,
            max_tokens=500,
            timeout=5.0
        )
        elapsed = time.time() - start_time
        logger.info(f"Groq API call succeeded in {elapsed:.2f}s")
        
        response_text = completion.choices[0].message.content
        tokens_used = completion.usage.total_tokens if completion.usage else 0
        return response_text, tokens_used, elapsed
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Groq API call failed after {elapsed:.2f}s: {e}")
        raise e

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    reraise=True
)
def summarize_history(history: list, existing_summary: str = None) -> str:
    """
    Summarizes conversation history using Groq.
    """
    client = get_client()
    
    history_text = ""
    for turn in history:
        history_text += f"User: {turn['query']}\n"
        if 'response' in turn and turn['response']:
            history_text += f"Jarvis: {turn['response']}\n"
            
    prompt = (
        f"You are a conversation summarization engine.\n"
        f"Existing summary: {existing_summary or 'None'}\n\n"
        f"New conversation turns:\n{history_text}\n\n"
        f"Please write a revised summary of the conversation history, combining the existing summary and new turns. "
        f"Keep the summary very concise, factual, and under 150 words. Do not add introductory or concluding remarks."
    )
    
    messages = [
        {"role": "system", "content": "You summarize conversation history into bullet points of key facts."},
        {"role": "user", "content": prompt}
    ]
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant", # Use faster model for background summarization
            messages=messages,
            temperature=0.3,
            max_tokens=250,
            timeout=5.0
        )
        return completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Groq history summarization failed: {e}")
        raise e
