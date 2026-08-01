# backend/app/core/config.py
# Sets up LLM model configuration — secrets from .env, structure from guardrails/config.yml

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
    engine: str
    model_name: str
    temperature: float = 0.2
    max_tokens: int = 512
    api_url: Optional[str] = None
    api_key: Optional[str] = None
    send_model_field: bool = True   # False for servers that 404 on a "model" key in payload


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
    Both self-hosted and OpenRouter use engine: openai in config.yml, so we
    distinguish which secret to inject by matching on base_url.
    """
    if base_url and "openrouter.ai" in base_url:
        return settings.openrouter_api_key
    if base_url and settings.self_hosted_api_url and base_url == settings.self_hosted_api_url:
        return settings.self_hosted_auth_token
    return settings.openai_api_key


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
                send_model_field=params.get("send_model_field", True),
            )

    raise ValueError(f"No model configured for role '{role}' in config.yml")