from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os

class Settings(BaseSettings):
    # Environment
    ENV: str
    
    # Database
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    DATABASE_URL: Optional[str] = None

    # ClickHouse
    CLICKHOUSE_HOST: str
    CLICKHOUSE_PORT: int
    CLICKHOUSE_DB: str
    CLICKHOUSE_USER: str
    CLICKHOUSE_PASSWORD: str
    CLICKHOUSE_READONLY_PASSWORD: Optional[str] = None

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str
    KAFKA_TOPIC: str
    KAFKA_ACTIVITY_TOPIC: str = "bank_activity_events"
    KAFKA_USER: Optional[str] = None
    KAFKA_PASSWORD: Optional[str] = None

    # Security
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    ACCOUNT_ENCRYPTION_KEY: str

    # Internal Services
    SIMULATOR_URL: str
    GATEWAY_API_KEY: str
    SIMULATOR_API_KEY: str
    TURNSTILE_SECRET_KEY: Optional[str] = "1x0000000000000000000000000000000AA"
    CORS_ORIGINS: str = "http://localhost:3000"
    ADMIN_EMAIL: str = "admin@karinbank.com"
    ADMIN_PASSWORD: str = "admin123"
    STRIPE_API_KEY: Optional[str] = "sk_test_placeholder"
    STRIPE_WEBHOOK_SECRET: Optional[str] = "whsec_placeholder"
    STRIPE_MOCK_URL: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=(
            os.path.realpath(os.path.join(os.path.dirname(__file__), "../.env.prod"))
            if os.getenv("ENV") == "production"
            else os.path.realpath(os.path.join(os.path.dirname(__file__), "../.env.dev"))
        ),
        extra="ignore"
    )

    def __init__(self, **values):
        super().__init__(**values)
        if not self.DATABASE_URL:
            self.DATABASE_URL = f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

settings = Settings()
