# backend/app/core/config.py

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel


class Settings(BaseSettings):
    openai_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
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
    role: str
    engine: str          # NeMo's field name — "openai" or "FastEmbed" etc.
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
    config_file = base_dir / "config.yml"

    if not config_file.exists():
        raise FileNotFoundError(f"Guardrails config not found at {config_file}")

    with open(config_file, "r") as f:
        return yaml.safe_load(f)


def _resolve_api_key(base_url: Optional[str], settings: Settings) -> Optional[str]:
    """
    Since both self-hosted and OpenRouter use engine: openai, we distinguish
    which secret to inject by matching on base_url instead of a provider name.
    """
    if base_url and "openrouter.ai" in base_url:
        return settings.openrouter_api_key
    if base_url and settings.self_hosted_api_url and base_url == settings.self_hosted_api_url:
        return settings.self_hosted_auth_token
    return settings.openai_api_key  # default: real OpenAI, or no base_url override


def get_model_spec(role: str = "main") -> ModelSpec:
    settings = get_settings()
    config = _load_raw_model_config()

    for entry in config.get("models", []):
        if entry.get("type") == role:
            params = entry.get("parameters", {})
            base_url = params.get("base_url")

            return ModelSpec(
                role=role,
                engine=entry["engine"],
                model_name=entry["model"],
                temperature=params.get("temperature", 0.2),
                max_tokens=params.get("max_tokens", 512),
                api_url=base_url,
                api_key=_resolve_api_key(base_url, settings),
            )

    raise ValueError(f"No model configured for role '{role}' in config.yml")