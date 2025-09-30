"""
Platform configuration management.
"""

import os

from pydantic_settings import BaseSettings


class PlatformConfig(BaseSettings):
    """Platform configuration settings."""

    # Environment
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = os.getenv("DEBUG", "true").lower() == "true"

    # API Server
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))

    # Kubernetes
    use_kubernetes: bool = os.getenv("USE_KUBERNETES", "false").lower() == "true"
    kubernetes_namespace_prefix: str = os.getenv("K8S_NAMESPACE_PREFIX", "sim")

    # Database (for future use)
    database_url: str | None = os.getenv("DATABASE_URL")

    # Redis (for future use)
    redis_url: str | None = os.getenv("REDIS_URL")

    # Observability
    jaeger_endpoint: str = os.getenv("JAEGER_ENDPOINT", "http://jaeger:14268/api/traces")
    prometheus_endpoint: str = os.getenv("PROMETHEUS_ENDPOINT", "http://prometheus:9090")
    loki_endpoint: str = os.getenv("LOKI_ENDPOINT", "http://loki:3100")

    # LLM Configuration (for future use)
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-3.5-turbo")

    # Traffic Generation
    default_traffic_duration: str = os.getenv("DEFAULT_TRAFFIC_DURATION", "5m")
    max_concurrent_traffic_jobs: int = int(os.getenv("MAX_TRAFFIC_JOBS", "10"))

    # Chaos Engineering
    max_concurrent_chaos_experiments: int = int(os.getenv("MAX_CHAOS_EXPERIMENTS", "5"))
    chaos_safety_mode: bool = os.getenv("CHAOS_SAFETY_MODE", "true").lower() == "true"

    # Resource Limits
    max_services_per_simulation: int = int(os.getenv("MAX_SERVICES_PER_SIMULATION", "50"))
    max_concurrent_simulations: int = int(os.getenv("MAX_CONCURRENT_SIMULATIONS", "10"))
    simulation_timeout_minutes: int = int(os.getenv("SIMULATION_TIMEOUT_MINUTES", "60"))

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_format: str = os.getenv("LOG_FORMAT", "json")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global configuration instance
config = PlatformConfig()


def get_config() -> PlatformConfig:
    """Get the global configuration instance."""
    return config


def is_development() -> bool:
    """Check if running in development mode."""
    return config.environment == "development"


def is_production() -> bool:
    """Check if running in production mode."""
    return config.environment == "production"


def should_use_kubernetes() -> bool:
    """Check if Kubernetes should be used."""
    # Auto-detect if running in Kubernetes
    in_k8s = os.getenv("KUBERNETES_SERVICE_HOST") is not None
    return config.use_kubernetes or in_k8s
