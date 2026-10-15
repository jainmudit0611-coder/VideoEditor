import os
import logging
from typing import Dict, Any, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("brand-guardian-config")

class Settings(BaseSettings):
    """
    Centralized Configuration for Brand Guardian AI Platform (Phase 3).
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # --- ENVIRONMENT & RUNTIME MODE ---
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    ALLOWED_HOSTS: str = "localhost,127.0.0.1"
    APP_VERSION: str = "3.0.0"
    LOG_FORMAT: str = "json"
    LOG_LEVEL: str = "INFO"

    # --- DATABASE CONFIGURATION ---
    DATABASE_URL: str = "sqlite:///./brand_guardian.db"

    # --- REDIS QUEUE CONFIGURATION ---
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_REQUIRED: bool = False
    QUEUE_PROCESSING_TIMEOUT_SECONDS: int = 300
    QUEUE_HEARTBEAT_INTERVAL_SECONDS: int = 15
    QUEUE_DEAD_LETTER_NAME: str = "brand_guardian_audit_dlq"
    QUEUE_PROCESSING_NAME: str = "brand_guardian_audit_processing"

    # --- RESOURCE & SAFETY LIMITS ---
    MAX_VIDEO_SIZE_MB: int = 500
    MAX_VIDEO_DURATION_SECONDS: int = 3600
    MAX_FRAMES: int = 20
    MAX_VISION_FRAMES: int = 10
    MAX_RETRIES: int = 3
    AUDIT_RETENTION_DAYS: int = 30

    # --- SECURITY & JWT AUTHENTICATION ---
    JWT_SECRET_KEY: str = "brand-guardian-dev-insecure-secret-key-change-in-prod"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    CORS_ORIGINS: str = "http://localhost:4200,http://127.0.0.1:4200"

    # --- AZURE STORAGE & BLOB ---
    AZURE_STORAGE_CONNECTION_STRING: Optional[str] = None

    # --- AZURE OPENAI ---
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_ENDPOINT: Optional[str] = None
    AZURE_OPENAI_API_VERSION: Optional[str] = "2024-08-01-preview"
    AZURE_OPENAI_CHAT_DEPLOYMENT: Optional[str] = None
    AZURE_OPENAI_DEPLOYMENT: Optional[str] = None
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: Optional[str] = None
    AZURE_OPENAI_TIMEOUT_SECONDS: float = 30.0
    AZURE_OPENAI_MAX_RETRIES: int = 2

    # --- AZURE AI SEARCH ---
    AZURE_SEARCH_ENDPOINT: Optional[str] = None
    AZURE_SEARCH_API_KEY: Optional[str] = None
    AZURE_SEARCH_INDEX_NAME: Optional[str] = "compliance-rules-index"
    AZURE_SEARCH_TIMEOUT_SECONDS: float = 15.0

    # --- AZURE VIDEO INDEXER ---
    AZURE_VI_NAME: Optional[str] = "project-brand-guardian-001"
    AZURE_VI_LOCATION: Optional[str] = None
    AZURE_VI_ACCOUNT_ID: Optional[str] = None
    AZURE_SUBSCRIPTION_ID: Optional[str] = None
    AZURE_RESOURCE_GROUP: Optional[str] = None
    AZURE_VI_TIMEOUT_SECONDS: float = 30.0

    # --- OBSERVABILITY ---
    APPLICATIONINSIGHTS_CONNECTION_STRING: Optional[str] = None
    LANGCHAIN_TRACING_V2: Optional[str] = None
    LANGCHAIN_ENDPOINT: Optional[str] = None
    LANGCHAIN_API_KEY: Optional[str] = None
    LANGCHAIN_PROJECT: Optional[str] = None

    def validate_environment(self) -> Dict[str, str]:
        """
        Validates environment configuration without printing or exposing secrets.
        Returns a dictionary mapping service keys to 'configured' or 'missing'.
        """
        services = {
            "ENVIRONMENT": self.ENVIRONMENT,
            "DATABASE_URL": "configured" if self.DATABASE_URL else "missing",
            "JWT_SECRET_KEY": "configured" if self.JWT_SECRET_KEY else "missing",
            "REDIS_URL": "configured" if self.REDIS_URL else "missing",
            "REDIS_REQUIRED": "true" if self.REDIS_REQUIRED else "false",
            "AZURE_OPENAI_ENDPOINT": "configured" if self.AZURE_OPENAI_ENDPOINT else "missing",
            "AZURE_OPENAI_API_KEY": "configured" if self.AZURE_OPENAI_API_KEY else "missing",
            "AZURE_OPENAI_CHAT_DEPLOYMENT": "configured" if (self.AZURE_OPENAI_CHAT_DEPLOYMENT or self.AZURE_OPENAI_DEPLOYMENT) else "missing",
            "AZURE_SEARCH_ENDPOINT": "configured" if self.AZURE_SEARCH_ENDPOINT else "missing",
            "AZURE_SEARCH_API_KEY": "configured" if self.AZURE_SEARCH_API_KEY else "missing",
            "AZURE_VI_ACCOUNT_ID": "configured" if self.AZURE_VI_ACCOUNT_ID else "missing",
            "AZURE_VI_LOCATION": "configured" if self.AZURE_VI_LOCATION else "missing",
            "AZURE_SUBSCRIPTION_ID": "configured" if self.AZURE_SUBSCRIPTION_ID else "missing",
            "AZURE_RESOURCE_GROUP": "configured" if self.AZURE_RESOURCE_GROUP else "missing",
        }
        return services

    def validate_production_configuration(self, raise_on_error: bool = False) -> Dict[str, Any]:
        """
        Validates security-sensitive production configuration settings.
        Ensures production deployments do not silently fall back to insecure defaults.
        """
        issues = []
        is_prod = self.ENVIRONMENT.lower() == "production"

        insecure_keys = {
            "brand-guardian-dev-insecure-secret-key-change-in-prod",
            "secret",
            "changeme",
            "test",
            "development",
            "insecure"
        }
        if is_prod:
            if not self.JWT_SECRET_KEY or self.JWT_SECRET_KEY in insecure_keys:
                issues.append("Production requires a strong, unique JWT_SECRET_KEY (cannot be default development placeholder).")
            elif len(self.JWT_SECRET_KEY) < 32:
                issues.append("Production JWT_SECRET_KEY must be at least 32 characters long.")

            if not self.DATABASE_URL or ":memory:" in self.DATABASE_URL:
                issues.append("Production requires a persistent, non-in-memory DATABASE_URL.")

            if not self.REDIS_REQUIRED:
                issues.append("Production requires REDIS_REQUIRED=true to prevent silent in-memory queue fallback.")

            origins = [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]
            if "*" in origins:
                issues.append("Production CORS_ORIGINS must not contain wildcard ('*') when credentials are enabled.")
            if not origins:
                issues.append("Production requires explicitly configured CORS_ORIGINS.")

            if self.DEBUG:
                issues.append("Production mode requires DEBUG=False.")

        result = {
            "environment": self.ENVIRONMENT,
            "is_production": is_prod,
            "status": "VALID" if not issues else "INVALID",
            "issues": issues
        }

        if raise_on_error and issues:
            raise ValueError(f"Production configuration validation failed: {'; '.join(issues)}")

        return result

# Instantiate global settings singleton
settings = Settings()

