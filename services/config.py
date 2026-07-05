from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
RECORDINGS_DIR = DATA_DIR / "recordings"
LOGS_DIR = DATA_DIR / "logs"
DATABASE_PATH = BASE_DIR / "db" / "application.db"
OLLAMA_PRIMARY = "http://192.168.1.101:11434" # Gaming PC
OLLAMA_PRIMARY_MODEL = "gemma4:e4b"

OLLAMA_FALLBACK = "http://192.168.0.119:11434" # Mini Pc
OLLAMA_FALLBACK_MODEL = "gemma4"

def ensure_directories():
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)