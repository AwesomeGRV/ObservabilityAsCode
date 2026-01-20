"""
Application configuration settings
"""

import os
from typing import List, Optional
from pydantic import BaseSettings, validator


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    app_name: str = "Observability as Code API"
    app_version: str = "2.0.0"
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # API
    api_prefix: str = "/api/v1"
    allowed_origins: List[str] = ["*"]
    max_request_size: int = 10 * 1024 * 1024  # 10MB
    
    # Security
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    access_token_expire_minutes: int = 30
    algorithm: str = "HS256"
    
    # Database
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://obs_user:obs_password@localhost:5432/observability"
    )
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_pool_timeout: int = 30
    database_pool_recycle: int = 300
    
    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_expire_time: int = 3600  # 1 hour
    
    # New Relic
    new_relic_account_id: Optional[str] = os.getenv("NEW_RELIC_ACCOUNT_ID")
    new_relic_api_key: Optional[str] = os.getenv("NEW_RELIC_API_KEY")
    new_relic_region: str = os.getenv("NEW_RELIC_REGION", "US")
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_format: str = "json"
    
    # Monitoring
    enable_metrics: bool = os.getenv("ENABLE_METRICS", "true").lower() == "true"
    metrics_port: int = 9090
    
    # Pagination
    default_page_size: int = 50
    max_page_size: int = 100
    
    # Coverage thresholds
    coverage_excellent_threshold: float = 90.0
    coverage_good_threshold: float = 75.0
    coverage_fair_threshold: float = 60.0
    coverage_poor_threshold: float = 40.0
    
    # Compliance
    compliance_standards: List[str] = ["standard", "enhanced", "strict"]
    default_compliance_standard: str = "standard"
    
    # Deployment
    deployment_timeout: int = 1800  # 30 minutes
    max_concurrent_deployments: int = 5
    
    @validator("allowed_origins", pre=True)
    def parse_allowed_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("database_url")
    def validate_database_url(cls, v):
        if not v:
            raise ValueError("DATABASE_URL is required")
        return v
    
    @validator("secret_key")
    def validate_secret_key(cls, v):
        if v == "your-secret-key-change-in-production":
            if os.getenv("ENVIRONMENT") == "production":
                raise ValueError("SECRET_KEY must be set in production")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Create settings instance
settings = Settings()
