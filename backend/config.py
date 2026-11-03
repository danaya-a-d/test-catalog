import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)


DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    DB_CONFIG = {
        "dsn": DATABASE_URL
    }
else:
    DB_CONFIG = {
        "host": os.getenv("POSTGRES_HOST"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "user": os.getenv("POSTGRES_USER"),
        "password": os.getenv("POSTGRES_PASSWORD"),
        "database": os.getenv("POSTGRES_DB"),
    }


MINIO_CONFIG = {
    "endpoint": os.getenv("MINIO_ENDPOINT"),
    "access_key": os.getenv("MINIO_ROOT_USER"),
    "secret_key": os.getenv("MINIO_ROOT_PASSWORD"),
    "secure": False
}

INTERNAL_API_KEY = os.environ["INTERNAL_API_KEY"]