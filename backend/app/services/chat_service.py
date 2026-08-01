# backend/app/services/chat_service.py

import asyncio
from functools import lru_cache
from pathlib import Path

from nemoguardrails import LLMRails, RailsConfig

from app.core.logging import get_app_logger, log_audit_event
from app.llm.factory import get_llm

GUARDRAILS_CONFIG_PATH = Path(__file__).parent.parent.parent / "guardrails"

logger = get_app_logger()


@lru_cache
def get_rails() -> LLMRails:
    """
    Builds the LLMRails instance ONCE per process (cached, same pattern as
    get_llm). This is what loads guardrails/config.yml, guardrails/kb/*.md,
    embeds the KB, and wires up the input/dialog/retrieval/output rails.

    Expensive to build (embedding the whole KB), cheap to reuse — so this
    must NOT be rebuilt per request.
    """
    logger.info(f"Loading guardrails config from {GUARDRAILS_CONFIG_PATH}")
    config = RailsConfig.from_path(str(GUARDRAILS_CONFIG_PATH))
    main_llm = get_llm("main")
    rails = LLMRails(config, llm=main_llm)
    logger.info("Guardrails + KB loaded and ready")
    return rails


async def handle_chat_message(
    session_id: str,
    user_message: str,
    history: list[dict] | None = None,
) -> dict:
    """
    Single entry point called by the FastAPI /v1/chat/completions route.
    Runs the message through the full rails pipeline (input -> retrieval ->
    LLM -> output) and returns the final response.
    """
    rails = get_rails()
    messages = (history or []) + [{"role": "user", "content": user_message}]

    response = await rails.generate_async(messages=messages)

    bot_message = response.get("content", str(response)) if isinstance(response, dict) else response

    # Pull whatever rail-trigger info NeMo exposes for this turn, for audit logging
    triggered_rails = response.get("triggered_rails", []) if isinstance(response, dict) else []

    log_audit_event(
        user_intent=user_message[:200],  # truncate — audit log isn't a full transcript store
        triggered_rails=triggered_rails,
        has_pii=False,   # placeholder until pii-detection action reports this back
        escalation_type=None,
    )

    return {
        "session_id": session_id,
        "message": bot_message,
    }