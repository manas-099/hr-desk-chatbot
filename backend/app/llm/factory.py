# backend/app/llm/factory.py   (adjust path if your folder is app/llms/)

from functools import lru_cache

from langchain_core.language_models.llms import LLM

from app.core.config import ModelSpec, get_model_spec
from app.llm.base import build_http_llm   # adjust import path to match your actual folder name


def build_llm(spec: ModelSpec) -> LLM:
    """
    Takes a resolved ModelSpec and returns a ready-to-use LangChain LLM.
    Both self-hosted and OpenRouter use engine: openai with a custom base_url,
    so they're handled the same way here — distinguished only by whether
    api_url is set.
    """
    if spec.engine == "openai" and spec.api_url:
        # Self-hosted or OpenRouter — both OpenAI-compatible endpoints
        return build_http_llm(spec)

    if spec.engine == "openai":
        # Real OpenAI, no custom base_url
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=spec.model_name,
            api_key=spec.api_key,
            temperature=spec.temperature,
            max_tokens=spec.max_tokens,
        )

    raise ValueError(f"No LLM builder registered for engine '{spec.engine}'")


@lru_cache
def get_llm(role: str = "main") -> LLM:
    spec = get_model_spec(role)
    return build_llm(spec)