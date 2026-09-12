from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    APP_NAME: str = "KisanSetu - Farmer Trust Passport"
    APP_VERSION: str = "1.0.0-mvp"
    DEBUG: bool = True

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./kisansetu.db")

    SECRET_KEY: str = os.getenv("SECRET_KEY", "kisansetu-dev-secret-key-change-in-production-2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours for demo

    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # Scoring weights (sum = 1.0)
    WEIGHT_PRODUCTION_STABILITY: float = 0.25
    WEIGHT_MARKET_STABILITY: float = 0.20
    WEIGHT_REPAYMENT_CAPACITY: float = 0.25
    WEIGHT_AGRICULTURAL_RISK: float = 0.15
    WEIGHT_FPO_COMMUNITY: float = 0.15

    # Scoring methodology version
    SCORING_VERSION: str = "1.0-baseline-statistical"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
