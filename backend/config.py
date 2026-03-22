"""Configuration management for the KarinBank application.

This module uses Pydantic Settings to load and validate environment variables
from .env files, providing a centralized settings object for the application.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from cryptography.fernet import Fernet
from typing import Optional
import os

# Environment detection
current_env = os.getenv("ENV", "development")
env_file_path = (
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env.prod"))
    if current_env == "production"
    else os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env.dev"))
)

class Settings(BaseSettings):
    """Application settings and configuration.

    Defines all environment variables required by the application, including
    database connections, Kafka configuration, and security keys.
    """
    # Environment
    ENV: str

    # Initial Admin Setup (Loaded from .env.dev, used by migrations)
    ADMIN_EMAIL: Optional[str] = None
    ADMIN_PASSWORD: Optional[str] = None

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

    # Kafka - Core settings
    KAFKA_BOOTSTRAP_SERVERS: str
    KAFKA_TOPIC: str
    KAFKA_ACTIVITY_TOPIC: str

    # Kafka security (optional for SASL/SSL)
    KAFKA_USER: Optional[str] = None
    KAFKA_PASSWORD: Optional[str] = None
    KAFKA_SSL_CA_PATH: Optional[str] = None
    KAFKA_SSL_CERT_PATH: Optional[str] = None
    KAFKA_SSL_KEY_PATH: Optional[str] = None

    # Kafka consumer group configuration
    KAFKA_CONSUMER_GROUP: str

    # Kafka producer settings
    KAFKA_REQUEST_TIMEOUT_MS: int
    KAFKA_ACKS: str
    KAFKA_RETRY_MAX_RETRIES: int
    KAFKA_RETRY_BACKOFF_MS: int
    KAFKA_RETRY_MAX_DELAY_MS: Optional[int] = None

    # Kafka DLQ (Dead Letter Queue) topic
    KAFKA_DLQ_TOPIC: str

    # Security & Encryption
    ACCOUNT_ENCRYPTION_KEY: str
    KAFKA_MESSAGE_ENCRYPTION_KEY: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    CORS_ORIGINS: str
    ABA_PREFIX: str
    
    # Cloudflare Turnstile
    TURNSTILE_SECRET_KEY: Optional[str] = None

    # Deposit Mock / Gateway Settings
    DEPOSIT_MOCK_API_KEY: str
    DEPOSIT_MOCK_WEBHOOK_SECRET: str
    DEPOSIT_MOCK_URL: Optional[str] = None
    
    # Vendor Simulator & Fed Gateway
    SIMULATOR_URL: str
    SIMULATOR_API_KEY: str
    GATEWAY_API_KEY: str

    model_config = SettingsConfigDict(
        env_file=env_file_path if os.path.exists(env_file_path) else None,
        env_file_encoding='utf-8',
        extra="ignore"
    )

    @field_validator("KAFKA_MESSAGE_ENCRYPTION_KEY")
    @classmethod
    def validate_kafka_key(cls, v: str) -> str:
        if v == "<GENERATE_FERNET_KEY_HERE>":
            raise ValueError("KAFKA_MESSAGE_ENCRYPTION_KEY must be a valid Fernet key, not the placeholder.")
        try:
            # Ensure it's a valid Fernet key
            Fernet(v.encode())
        except Exception as e:
            raise ValueError(f"Invalid Fernet key for KAFKA_MESSAGE_ENCRYPTION_KEY: {e}")
        return v

    def __init__(self, **values):
        super().__init__(**values)
        if not self.DATABASE_URL:
            self.DATABASE_URL = f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

settings = Settings()
