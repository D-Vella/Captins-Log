from pathlib import Path
import dotenv

dotenv.load_dotenv()

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
RECORDINGS_DIR = DATA_DIR / "recordings"
LOGS_DIR = DATA_DIR / "logs"
DATABASE_PATH = BASE_DIR / "db" / "application.db"

DATABASE_BACKEND = dotenv.get_key(".env", "DATABASE_BACKEND")
if DATABASE_BACKEND is None:
    DATABASE_BACKEND = "sqlite"

def get_database_url():
    if DATABASE_BACKEND == "sqlite":
        return f"sqlite:///{DATABASE_PATH}"
    elif DATABASE_BACKEND == "postgresql":
        POSTGRES_CONFIG = {
            "dbname": dotenv.get_key(".env", "POSTGRES_DB"),
            "user": dotenv.get_key(".env", "POSTGRES_USER"),
            "password": dotenv.get_key(".env", "POSTGRES_PASSWORD"),
            "host": dotenv.get_key(".env", "POSTGRES_HOST"),
            "port": dotenv.get_key(".env", "POSTGRES_PORT")
        }
        return f"postgresql://{POSTGRES_CONFIG['user']}:{POSTGRES_CONFIG['password']}@{POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}/{POSTGRES_CONFIG['dbname']}"
    else:
        raise ValueError(f"Unsupported database backend: {DATABASE_BACKEND}")

OLLAMA_PRIMARY = dotenv.get_key(".env", "OLLAMA_PRIMARY")
OLLAMA_PRIMARY_MODEL = dotenv.get_key(".env", "OLLAMA_PRIMARY_MODEL")

OLLAMA_FALLBACK = dotenv.get_key(".env", "OLLAMA_FALLBACK")
OLLAMA_FALLBACK_MODEL = dotenv.get_key(".env", "OLLAMA_FALLBACK_MODEL")

def ensure_directories():
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

POSTGRES_CONFIG = {
    "dbname": dotenv.get_key(".env", "POSTGRES_DB"),
    "user": dotenv.get_key(".env", "POSTGRES_USER"),
    "password": dotenv.get_key(".env", "POSTGRES_PASSWORD"),
    "host": dotenv.get_key(".env", "POSTGRES_HOST"),
    "port": dotenv.get_key(".env", "POSTGRES_PORT")
}