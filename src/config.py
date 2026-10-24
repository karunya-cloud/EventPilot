"""Configuration management for EventPilot AI."""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

class Settings:
    """Application settings and configuration."""
    APP_ENV: str = os.getenv("APP_ENV", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        f"sqlite:///{BASE_DIR / 'eventpilot.db'}"
    )

    # Fetch.ai / Agentverse Seeds & Ports
    AGENTVERSE_API_KEY: str = os.getenv("AGENTVERSE_API_KEY", "")
    
    COORDINATOR_SEED: str = os.getenv("COORDINATOR_SEED", "eventpilot_coord_seed_2026")
    PLANNING_SEED: str = os.getenv("PLANNING_SEED", "eventpilot_plan_seed_2026")
    LOGISTICS_SEED: str = os.getenv("LOGISTICS_SEED", "eventpilot_logistics_seed_2026")
    REGISTRATION_SEED: str = os.getenv("REGISTRATION_SEED", "eventpilot_reg_seed_2026")
    COMMUNICATION_SEED: str = os.getenv("COMMUNICATION_SEED", "eventpilot_comm_seed_2026")
    RISK_SEED: str = os.getenv("RISK_SEED", "eventpilot_risk_seed_2026")

    COORDINATOR_PORT: int = int(os.getenv("COORDINATOR_PORT", "8000"))
    PLANNING_PORT: int = int(os.getenv("PLANNING_PORT", "8001"))
    LOGISTICS_PORT: int = int(os.getenv("LOGISTICS_PORT", "8002"))
    REGISTRATION_PORT: int = int(os.getenv("REGISTRATION_PORT", "8003"))
    COMMUNICATION_PORT: int = int(os.getenv("COMMUNICATION_PORT", "8004"))
    RISK_PORT: int = int(os.getenv("RISK_PORT", "8005"))

    API_HOST: str = os.getenv("API_HOST", "127.0.0.1")
    API_PORT: int = int(os.getenv("API_PORT", "8080"))

    # Security & Execution Controls
    MOCK_EXTERNAL_ACTIONS: bool = os.getenv("MOCK_EXTERNAL_ACTIONS", "True").lower() in ("true", "1", "yes")
    ALLOW_AUTO_EMAIL: bool = os.getenv("ALLOW_AUTO_EMAIL", "False").lower() in ("true", "1", "yes")
    QR_SIGNING_SECRET: str = os.getenv("QR_SIGNING_SECRET", "eventpilot_super_secret_hmac_key_2026")

    # LLM Settings
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")

settings = Settings()
