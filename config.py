import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Set up logging format
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("ResumeMatcherConfig")

# Load environment variables from .env file
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_API_BASE_URL = os.getenv("TELEGRAM_API_BASE_URL", "").strip()
TELEGRAM_PROXY = os.getenv("TELEGRAM_PROXY", "").strip()

# WhatsApp Cloud API Configurations
WHATSAPP_API_TOKEN = os.getenv("WHATSAPP_API_TOKEN", "").strip()
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "").strip()
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "resume_bot_verify_token").strip()
WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v19.0").strip()

# OpenRouter / OpenAI API Key support
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", os.getenv("OPENAI_API_KEY", "")).strip()
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip()
OPENAI_MODEL = os.getenv("OPENROUTER_MODEL", os.getenv("OPENAI_MODEL", "openai/gpt-4o-mini")).strip()
PORT = int(os.getenv("PORT", "8000"))

# File upload limits & directories
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

def validate_config(require_telegram: bool = True, require_ai: bool = True, require_openai: bool = None) -> tuple[bool, list[str]]:
    """
    Validates that required configuration environment variables are loaded.
    Returns (is_valid, list_of_error_messages).
    """
    errors = []
    
    check_ai = require_ai if require_openai is None else require_openai

    if require_telegram and not TELEGRAM_BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN is missing in environment or .env file.")
        
    if check_ai and not OPENROUTER_API_KEY:
        errors.append("OPENROUTER_API_KEY is missing in environment or .env file.")
        
    if errors:
        for err in errors:
            logger.warning(f"Config Warning: {err}")
        return False, errors
        
    logger.info("Configuration validated successfully.")
    return True, []
