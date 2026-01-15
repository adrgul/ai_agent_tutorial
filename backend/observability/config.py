"""
Observability configuration and settings.

Centralized configuration for all observability features:
- Metrics collection
- Request correlation
- Environment labeling
- Feature flags

Environment variables:
    ENABLE_METRICS: Enable Prometheus metrics (default: true)
    ENVIRONMENT: Deployment environment (dev/staging/prod)
    TENANT_ID: Tenant identifier for multi-tenant deployments
    METRICS_PORT: Port for Prometheus /metrics endpoint (default: 8000)
"""
import os
from typing import Optional
from pydantic import BaseModel, Field


class ObservabilityConfig(BaseModel):
    """
    Configuration for observability features.
    
    All settings can be controlled via environment variables for
    different deployment environments (dev/staging/prod).
    """
    
    # Metrics settings
    enable_metrics: bool = Field(
        default=True,
        description="Enable Prometheus metrics collection"
    )
    
    metrics_port: int = Field(
        default=8000,
        description="Port for Prometheus /metrics HTTP endpoint"
    )
    
    # Environment settings
    environment: str = Field(
        default="dev",
        description="Deployment environment (dev/staging/prod)"
    )
    
    tenant_id: str = Field(
        default="default",
        description="Tenant identifier for multi-tenant scenarios"
    )
    
    version: str = Field(
        default="unknown",
        description="Application version for tracking deployments"
    )
    
    # Request correlation settings
    enable_request_correlation: bool = Field(
        default=True,
        description="Enable request ID generation and propagation"
    )
    
    # Logging settings
    enable_correlated_logging: bool = Field(
        default=True,
        description="Include request_id in log messages"
    )
    
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG/INFO/WARNING/ERROR)"
    )
    
    # LLM cost tracking settings
    enable_cost_tracking: bool = Field(
        default=True,
        description="Track estimated LLM costs in metrics"
    )
    
    @classmethod
    def from_env(cls) -> "ObservabilityConfig":
        """
        Load configuration from environment variables.
        
        Returns:
            ObservabilityConfig instance with values from env
        """
        return cls(
            enable_metrics=os.getenv("ENABLE_METRICS", "true").lower() == "true",
            metrics_port=int(os.getenv("METRICS_PORT", "8000")),
            environment=os.getenv("ENVIRONMENT", "dev"),
            tenant_id=os.getenv("TENANT_ID", "default"),
            version=os.getenv("APP_VERSION", "unknown"),
            enable_request_correlation=os.getenv("ENABLE_REQUEST_CORRELATION", "true").lower() == "true",
            enable_correlated_logging=os.getenv("ENABLE_CORRELATED_LOGGING", "true").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            enable_cost_tracking=os.getenv("ENABLE_COST_TRACKING", "true").lower() == "true",
        )
    
    def to_env_dict(self) -> dict:
        """
        Export configuration as environment variables dictionary.
        
        Useful for Docker Compose or container orchestration.
        """
        return {
            "ENABLE_METRICS": str(self.enable_metrics).lower(),
            "METRICS_PORT": str(self.metrics_port),
            "ENVIRONMENT": self.environment,
            "TENANT_ID": self.tenant_id,
            "APP_VERSION": self.version,
            "ENABLE_REQUEST_CORRELATION": str(self.enable_request_correlation).lower(),
            "ENABLE_CORRELATED_LOGGING": str(self.enable_correlated_logging).lower(),
            "LOG_LEVEL": self.log_level,
            "ENABLE_COST_TRACKING": str(self.enable_cost_tracking).lower(),
        }


def get_config() -> ObservabilityConfig:
    """
    Get current observability configuration.
    
    Returns:
        Configuration loaded from environment
    """
    return ObservabilityConfig.from_env()


# Singleton instance (lazy-loaded)
_config: Optional[ObservabilityConfig] = None


def get_global_config() -> ObservabilityConfig:
    """
    Get global observability configuration singleton.
    
    Returns:
        Cached configuration instance
    """
    global _config
    if _config is None:
        _config = ObservabilityConfig.from_env()
    return _config


def reload_config():
    """Reload configuration from environment (for testing or hot reload)."""
    global _config
    _config = None
