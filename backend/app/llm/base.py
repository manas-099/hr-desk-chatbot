# backend/app/llm/base.py

from typing import Any, List, Optional

import requests
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.language_models.llms import LLM

from app.core.config import ModelSpec
from app.core.logging import get_logger

TIMEOUT_SECONDS = 30
logger = get_logger("llm")


class HTTPChatLLM(LLM):
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

        logger.info(f"→ POST {url} | prompt_len={len(prompt)} chars")

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT_SECONDS)
            resp.raise_for_status()
            result = resp.json()
            content = result["choices"][0]["message"]["content"]

            logger.info(f"← {resp.status_code} | response_len={len(content)} chars")
            return content

        except requests.exceptions.Timeout:
            logger.error(f"✗ Timeout after {TIMEOUT_SECONDS}s | {url}")
            return "[LLM call failed: request timed out]"

        except requests.exceptions.ConnectionError:
            logger.error(f"✗ Connection refused | {url}")
            return "[LLM call failed: could not connect to model server]"

        except requests.exceptions.HTTPError:
            logger.error(f"✗ HTTP {resp.status_code} | {url} | body: {resp.text[:200]}")
            return f"[LLM call failed: {resp.status_code} error from server]"

        except (KeyError, IndexError):
            logger.error(f"✗ Unexpected response shape | {url} | raw: {resp.text[:200]}")
            return "[LLM call failed: unexpected response format]"

        except Exception as e:
            logger.exception(f"✗ Unhandled error | {url}")
            return f"[LLM call failed: {e}]"


def build_http_llm(spec: ModelSpec) -> HTTPChatLLM:
    if not spec.api_url:
        logger.error(f"No api_url set for role '{spec.role}'")
        raise ValueError(f"ModelSpec for role '{spec.role}' has no api_url set.")
    return HTTPChatLLM(
        model_name=spec.model_name,
        api_url=spec.api_url,
        api_key=spec.api_key,
        temperature=spec.temperature,
        max_tokens=spec.max_tokens,
        send_model_field=spec.send_model_field,
    )