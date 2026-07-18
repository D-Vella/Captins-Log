import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
RECORDINGS_DIR = DATA_DIR / "recordings"
LOGS_DIR = DATA_DIR / "logs"
DATABASE_PATH = BASE_DIR / "db" / "application.db"

DATABASE_BACKEND = os.getenv("DATABASE_BACKEND")
if DATABASE_BACKEND is None:
    DATABASE_BACKEND = "sqlite"

def get_database_url():
    if DATABASE_BACKEND == "sqlite":
        return f"sqlite:///{DATABASE_PATH}"
    elif DATABASE_BACKEND == "postgresql":
        POSTGRES_CONFIG = {
            "dbname": os.getenv("POSTGRES_DB"),
            "user": os.getenv("POSTGRES_USER"),
            "password": os.getenv("POSTGRES_PASSWORD"),
            "host": os.getenv("POSTGRES_HOST"),
            "port": os.getenv("POSTGRES_PORT")
        }
        return f"postgresql://{POSTGRES_CONFIG['user']}:{POSTGRES_CONFIG['password']}@{POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}/{POSTGRES_CONFIG['dbname']}"
    else:
        raise ValueError(f"Unsupported database backend: {DATABASE_BACKEND}")

OLLAMA_PRIMARY = os.getenv("OLLAMA_PRIMARY")
OLLAMA_PRIMARY_MODEL = os.getenv("OLLAMA_PRIMARY_MODEL")

OLLAMA_FALLBACK = os.getenv("OLLAMA_FALLBACK")
OLLAMA_FALLBACK_MODEL = os.getenv("OLLAMA_FALLBACK_MODEL")

WHISPER_SERVER_URL = os.getenv("WHISPER_SERVER_URL")

def ensure_directories():
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

POSTGRES_CONFIG = {
    "dbname": os.getenv("POSTGRES_DB"),
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
    "host": os.getenv("POSTGRES_HOST"),
    "port": os.getenv("POSTGRES_PORT")
}