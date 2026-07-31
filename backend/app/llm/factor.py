
# backend/app/llms/factory.py

from functools import lru_cache

from langchain_core.language_models.llms import LLM

from app.core.config import ModelSpec, get_model_spec
from app.llm.base import build_http_llm


def build_llm(spec: ModelSpec) -> LLM:
    """
    Single entry point: takes a resolved ModelSpec and returns a ready-to-use
    LangChain LLM instance. This is the ONLY function that knows how to turn
    a provider name into an actual client object.
    """
    if spec.provider in ("self_hosted", "openrouter"):
        # Both are OpenAI-compatible /chat/completions endpoints, just different
        # base URLs/keys — already resolved inside spec by config.py.
        return build_http_llm(spec)

    if spec.provider == "openai":
        pass


    raise ValueError(f"No LLM builder registered for provider '{spec.provider}'")


@lru_cache
def get_llm(role: str = "main") -> LLM:
    """
    What the rest of the app actually calls: get_llm("main"), get_llm("fact_judge").
    Cached per role so you're not rebuilding an HTTP client / ChatOpenAI instance
    on every single request — same LLM object gets reused across the app's lifetime.
    """
    spec = get_model_spec(role)
    return build_llm(spec)