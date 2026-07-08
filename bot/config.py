"""Configuration for TLDRBot."""
import os
import json


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


BOT_TOKEN = os.environ.get("BOT_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
AI_MODEL = os.environ.get("AI_MODEL", "gpt-4o-mini")
AI_BASE_URL = (
    os.environ.get("AI_BASE_URL")
    or os.environ.get("OPENAI_BASE_URL")
)
DATABASE_URL = os.environ.get("DATABASE_URL")
MAX_MESSAGES = int(os.environ.get("MAX_MESSAGES", "400"))
DAILY_LIMIT = int(os.environ.get("DAILY_LIMIT", "10"))
PORT = int(os.environ.get("PORT", "5000"))
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
AUTO_DOWNLOAD_ENABLED = _bool_env("AUTO_DOWNLOAD_ENABLED", False)
TOKEN_LIMIT_ENABLED = _bool_env("TOKEN_LIMIT_ENABLED", True)
TOKEN_LIMIT_MAX_INPUT_TOKENS = int(os.environ.get("TOKEN_LIMIT_MAX_INPUT_TOKENS", "64000"))
TOKENIZER_REPO_ID = os.environ.get("TOKENIZER_REPO_ID", "Qwen/Qwen3.6-27B")
TOKENIZER_REVISION = os.environ.get("TOKENIZER_REVISION", "main")
TOKENIZER_FILENAME = os.environ.get("TOKENIZER_FILENAME", "tokenizer.json")
TOKENIZER_CACHE_DIR = os.environ.get("TOKENIZER_CACHE_DIR", "data/tokenizers")
TOKENIZER_URL = os.environ.get("TOKENIZER_URL")
HF_TOKEN = os.environ.get("HF_TOKEN")

def validate_config():
    required = ["BOT_TOKEN"]
    if not AI_BASE_URL:
        required.append("OPENAI_API_KEY")
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        raise ValueError(f"Missing: {', '.join(missing)}")

_DEFAULT_VIDEO_URL_PATTERNS = [
    r'https?://(www\.)?tiktok\.com/',
    r'https?://(www\.)?vt.tiktok\.com/', 
    r'https?://vm\.tiktok\.com/',
    r'https?://(www\.)?instagram\.com/reel/',
    r'https?://(www\.)?youtube\.com/shorts/',
    r'https?://youtu\.be/',
]

_video_patterns_env = os.environ.get("VIDEO_URL_PATTERNS")
if _video_patterns_env:
    try:
        VIDEO_URL_PATTERNS = json.loads(_video_patterns_env)
        if not isinstance(VIDEO_URL_PATTERNS, list):
            raise ValueError("VIDEO_URL_PATTERNS must be a JSON array")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in VIDEO_URL_PATTERNS environment variable: {e}")
else:
    VIDEO_URL_PATTERNS = _DEFAULT_VIDEO_URL_PATTERNS

