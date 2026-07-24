"""
config.py
Central place for file paths and persistent configuration (JSON on disk).
No API keys are required for the app to work out of the box.
"""
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
MEMORY_FILE = os.path.join(DATA_DIR, "memory.json")
REMINDERS_FILE = os.path.join(DATA_DIR, "reminders.json")

DEFAULT_CONFIG = {
    "user_name": "there",
    "assistant_name": "Jarvis",
    "city": "Pune",
    "voice_enabled": True,
    "voice_rate": 175,
    "voice_volume": 1.0,
    "wake_word": "jarvis",
    "groq_api_key": "",         # optional: preferred LLM backend for chit-chat (fast + free tier)
    "groq_model": "llama-3.3-70b-versatile",
    "groq_vision_model": "qwen/qwen3.6-27b",  # Groq's current vision-capable model
    "openai_api_key": "",       # optional fallback if no Groq key is set
    "news_country": "in",
}


def load_config() -> dict:
    """Load config.json, creating it with defaults if missing."""
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        # backfill any keys added in newer versions
        merged = dict(DEFAULT_CONFIG)
        merged.update(cfg)
        return merged
    except (json.JSONDecodeError, OSError):
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)


def save_config(cfg: dict) -> None:
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def update_config(**kwargs) -> dict:
    cfg = load_config()
    cfg.update(kwargs)
    save_config(cfg)
    return cfg
