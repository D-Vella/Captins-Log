from pathlib import Path
import dotenv

dotenv.load_dotenv()

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
RECORDINGS_DIR = DATA_DIR / "recordings"
LOGS_DIR = DATA_DIR / "logs"
DATABASE_PATH = BASE_DIR / "db" / "application.db"

OLLAMA_PRIMARY = dotenv.get_key(".env", "OLLAMA_PRIMARY")
OLLAMA_PRIMARY_MODEL = dotenv.get_key(".env", "OLLAMA_PRIMARY_MODEL")

OLLAMA_FALLBACK = dotenv.get_key(".env", "OLLAMA_FALLBACK")
OLLAMA_FALLBACK_MODEL = dotenv.get_key(".env", "OLLAMA_FALLBACK_MODEL")

def ensure_directories():
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)