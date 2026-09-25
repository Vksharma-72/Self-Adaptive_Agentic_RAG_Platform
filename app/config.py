import os
from dotenv import load_dotenv


load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Settings:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    QDRANT_URL = os.getenv("QDRANT_CLUSTER_ENDPOINT")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
    QDRANT_COLLECTION = "enterprise_rag"  # legacy CLI-ingestion collection

    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_MODEL = "openai/gpt-oss-120b"
    GROQ_FALLBACK_API_KEY = os.getenv("GROQ_FALLBACK_API_KEY")
    PORTKEY_API_KEY = os.getenv("PORTKEY_API_KEY")
    PORTKEY_CONFIG = os.getenv("PORTKEY_CONFIG")

    GROQ_SLUG = os.getenv("GROQ_SLUG")
    GROQ_SLUG_2 = os.getenv("GROQ_SLUG_2")

    # --- Platform: auth ---
    JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRE_MINUTES = 60 * 24  # 24h
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

    # --- Platform: storage ---
    DB_PATH = os.getenv("DB_PATH", os.path.join(BASE_DIR, "platform.db"))
    UPLOADS_DIR = os.getenv("UPLOADS_DIR", os.path.join(BASE_DIR, "uploads"))

    # --- Platform: frontend ---
    FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

    # --- Optimization Lab (TurboQuant benchmarking) ---
    BENCH_SAMPLE_SIZE = int(os.getenv("BENCH_SAMPLE_SIZE", "1000"))
    BENCH_QUERY_COUNT = int(os.getenv("BENCH_QUERY_COUNT", "10"))


settings = Settings()
