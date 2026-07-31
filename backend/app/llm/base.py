# backend/app/llms/base.py

from typing import Any, List, Optional

import requests
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.language_models.llms import LLM

from app.core.config import ModelSpec

TIMEOUT_SECONDS = 30


class HTTPChatLLM(LLM):
    """
    Generic LangChain LLM wrapper for any OpenAI-compatible /chat/completions
    endpoint — covers BOTH your self-hosted model and OpenRouter, since both
    speak the same request/response shape. Only api_url/api_key/model_name differ.
    """

    model_name: str
    api_url: str
    api_key: Optional[str] = None
    temperature: float = 0.2
    max_tokens: int = 512

    @property
    def _llm_type(self) -> str:
        return "http_chat_llm"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if stop:
            payload["stop"] = stop

        try:
            resp = requests.post(
                self.api_url, headers=headers, json=payload, timeout=TIMEOUT_SECONDS
            )
            resp.raise_for_status()
            result = resp.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            # Never let a raw exception blow up a rail mid-flow — surface it
            # as text so self_check_facts/output rails can still run and the
            # failure gets caught by fact-checking rather than crashing the app.
            return f"[LLM call failed: {e}]"


def build_http_llm(spec: ModelSpec) -> HTTPChatLLM:
    if not spec.api_url:
        raise ValueError(
            f"ModelSpec for role '{spec.role}' (provider={spec.provider}) has no api_url set."
        )
    return HTTPChatLLM(
        model_name=spec.model_name,
        api_url=spec.api_url,
        api_key=spec.api_key,
        temperature=spec.temperature,
        max_tokens=spec.max_tokens,
    )