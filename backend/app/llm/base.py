# backend/app/llm/base.py

import logging
from typing import Any, List, Optional

import requests
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.language_models.llms import LLM

from app.core.config import ModelSpec

TIMEOUT_SECONDS = 30
logger = logging.getLogger("app")


class HTTPChatLLM(LLM):
    """
    Generic LangChain LLM wrapper for any OpenAI-compatible /chat/completions
    endpoint. Used for both self-hosted models and OpenRouter.
    """

    model_name: str
    api_url: str
    api_key: Optional[str] = None
    temperature: float = 0.2
    max_tokens: int = 512
    send_model_field: bool = True

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

        url = self.api_url.rstrip("/") + "/chat/completions"

        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if self.send_model_field:
            payload["model"] = self.model_name
        if stop:
            payload["stop"] = stop

        logger.info(f"[HTTPChatLLM] POST {url} | model_field_sent={self.send_model_field}")
        print(f"\n>>> [HTTPChatLLM] POST {url}")
        print(f">>> [HTTPChatLLM] payload keys: {list(payload.keys())}")

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT_SECONDS)
            print(f">>> [HTTPChatLLM] Status: {resp.status_code}")
            print(f">>> [HTTPChatLLM] Response body (first 500 chars): {resp.text[:500]}")
            resp.raise_for_status()
            result = resp.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"[HTTPChatLLM] Call failed: {e}")
            print(f">>> [HTTPChatLLM] FAILED: {e}")
            return f"[LLM call failed: {e}]"


def build_http_llm(spec: ModelSpec) -> HTTPChatLLM:
    if not spec.api_url:
        raise ValueError(f"ModelSpec for role '{spec.role}' has no api_url set.")
    return HTTPChatLLM(
        model_name=spec.model_name,
        api_url=spec.api_url,
        api_key=spec.api_key,
        temperature=spec.temperature,
        max_tokens=spec.max_tokens,
        send_model_field=spec.send_model_field,
    )