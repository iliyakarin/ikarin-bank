"""Configuration for the financial life simulator.

Reads directly from process environment variables (set via docker-compose's
env_file/environment blocks), same pattern as backend/config.py.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Target backend
    API_BASE_URL: str = "http://api:8000"

    # Primary demo persona. Must already exist - reuses the backend's own
    # ADMIN_EMAIL/ADMIN_PASSWORD seed admin account.
    ADMIN_EMAIL: str
    ADMIN_PASSWORD: str

    # Secondary demo persona. Auto-registered on first run if it doesn't exist.
    SIM_USER2_EMAIL: str
    SIM_USER2_PASSWORD: str

    # Shared secret bypassing Turnstile on /auth/login and /auth/register.
    # Must match SIMULATOR_SERVICE_KEY on the backend.
    SIMULATOR_SERVICE_KEY: str

    # Simulation cadence
    TICK_INTERVAL_SECONDS: int = 3600

    # Amounts, in cents
    SALARY_AMOUNT_CENTS: int = 250000
    RENT_AMOUNT_CENTS: int = 180000
    CAR_INSURANCE_AMOUNT_CENTS: int = 12000

    # Probability (0-1) per tick of firing a one-time merchant purchase / P2P transfer
    PURCHASE_CHANCE_PER_TICK: float = 0.15
    P2P_CHANCE_PER_TICK: float = 0.05

    STATE_DB_PATH: str = "/app/data/simulator_state.db"

    model_config = SettingsConfigDict(env_file=None)


settings = Settings()
