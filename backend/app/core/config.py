# backend/app/core/config.py
# config.py — sets up LLM model configuration (secrets from .env, structure from guardrails/config.yml)

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel


class Settings(BaseSettings):
    # API keys — one per provider you might use
    openai_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None

    # Self-hosted endpoint config
    self_hosted_api_url: Optional[str] = None
    self_hosted_auth_token: Optional[str] = None

    environment: str = "development"
    log_level: str = "INFO"
    guardrails_config_path: str = "guardrails"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


class ModelSpec(BaseModel):
    """One resolved model entry, normalized regardless of provider."""
    role: str
    provider: str
    model_name: str
    temperature: float = 0.2
    max_tokens: int = 512
    api_url: Optional[str] = None
    api_key: Optional[str] = None


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def _load_raw_model_config(config_dir: str | None = None) -> Dict[str, Any]:
    settings = get_settings()
    base_dir = Path(config_dir or settings.guardrails_config_path)
    config_file = base_dir / "config.yml"   # <-- fixed: .yml not .yaml

    if not config_file.exists():
        raise FileNotFoundError(f"Guardrails config not found at {config_file}")

    with open(config_file, "r") as f:
        return yaml.safe_load(f)


def _resolve_provider_credentials(provider: str, settings: Settings) -> tuple[Optional[str], Optional[str]]:
    """Returns (api_url, api_key) for a given provider name."""
    if provider == "openai":
        return None, settings.openai_api_key
    if provider == "openrouter":
        return "https://openrouter.ai/api/v1", settings.openrouter_api_key
    if provider == "self_hosted":
        return settings.self_hosted_api_url, settings.self_hosted_auth_token
    raise ValueError(f"Unknown provider '{provider}' — add it to _resolve_provider_credentials")


def get_model_spec(role: str = "main") -> ModelSpec:
    settings = get_settings()
    config = _load_raw_model_config()

    for entry in config.get("models", []):
        if entry.get("type") == role:
            provider = entry["provider"]
            api_url, api_key = _resolve_provider_credentials(provider, settings)

            return ModelSpec(
                role=role,
                provider=provider,
                model_name=entry["model"],
                temperature=entry.get("parameters", {}).get("temperature", 0.2),
                max_tokens=entry.get("parameters", {}).get("max_tokens", 512),
                api_url=entry.get("api_url", api_url),
                api_key=api_key,
            )

    raise ValueError(f"No model configured for role '{role}' in config.yml")