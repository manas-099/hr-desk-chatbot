# backend/guardrails/actions.py

import hashlib
import logging
import re
from datetime import datetime
from typing import Optional

from nemoguardrails.actions import action

logger = logging.getLogger("app")


def _get_user_text(context: Optional[dict]) -> str:
    """
    Safely pulls the user's message out of NeMo's context dict, regardless of
    which key is populated at this stage of the flow (last_user_message is
    often None during input rails; user_message holds the real value there).
    Always returns a string, never None.
    """
    if not context:
        return ""
    return (context.get("last_user_message") or context.get("user_message") or "")


def _get_bot_text(context: Optional[dict]) -> str:
    """Same safety pattern, for the bot's draft response during output rails."""
    if not context:
        return ""
    return (context.get("last_bot_message") or context.get("bot_message") or "")


def _get_chunks_text(context: Optional[dict]) -> str:
    """Same safety pattern, for retrieved KB chunks during retrieval rails."""
    if not context:
        return ""
    return context.get("relevant_chunks") or ""


# ---------------------------------------------------------------------------
# Input rail actions
# ---------------------------------------------------------------------------

@action()
async def self_check_input(context: Optional[dict] = None, llm=None) -> bool:
    """
    Placeholder safe-default check. Replace with a real LLM call using the
    self_check_input prompt from prompts.yml if you want model-based
    jailbreak/PII-request detection instead of just the keyword rail below.
    """
    user_input = _get_user_text(context)
    if not user_input:
        return True
    return True


@action()
async def detect_harassment_intent(context: Optional[dict] = None) -> bool:
    """Keyword-based harassment/complaint detection — no LLM call needed."""
    user_input = _get_user_text(context).lower()
    harassment_keywords = [
        "harassment", "harassed", "inappropriate", "uncomfortable",
        "discrimination", "retaliation", "hostile", "bullying",
        "sexual", "abuse", "threatened", "intimidated",
    ]
    return any(kw in user_input for kw in harassment_keywords)


@action()
async def create_anonymous_ticket(type: str = "general", context: Optional[dict] = None) -> str:
    """Mock ticket creation — swap for a real ServiceNow/Zendesk call later."""
    session_id = context.get("session_id", "unknown") if context else "unknown"
    ticket_id = (
        f"HR-{hashlib.sha256(session_id.encode()).hexdigest()[:8].upper()}"
        f"-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    )
    logger.info(f"Anonymous ticket created: {ticket_id}, type={type}")
    return ticket_id


# ---------------------------------------------------------------------------
# Retrieval rail actions
# ---------------------------------------------------------------------------

@action()
async def detect_pii_in_chunks(context: Optional[dict] = None) -> bool:
    """Checks if retrieved KB chunks contain unmasked PII markers."""
    chunks = _get_chunks_text(context).lower()
    sensitive_markers = [
        "ssn", "social security", "salary:", "compensation:",
        "employee id:", "dob:", "date of birth",
    ]
    return any(marker in chunks for marker in sensitive_markers)


@action()
async def mask_pii_in_chunks(context: Optional[dict] = None) -> str:
    """Masks PII patterns in retrieved chunks before the LLM ever sees them."""
    chunks = _get_chunks_text(context)
    chunks = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[SSN REDACTED]", chunks)
    chunks = re.sub(r"\$\d{1,3}(,\d{3})+(\.\d{2})?", "[COMPENSATION REDACTED]", chunks)
    chunks = re.sub(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b", "[CARD REDACTED]", chunks)
    return chunks


@action()
async def detect_draft_policy(context: Optional[dict] = None) -> bool:
    """Detects if any retrieved chunk is marked draft/unapproved."""
    chunks = _get_chunks_text(context).lower()
    draft_markers = ["draft", "unapproved", "pending review", "not yet effective", "proposed"]
    return any(marker in chunks for marker in draft_markers)


@action()
async def filter_draft_chunks(context: Optional[dict] = None) -> str:
    """Strips draft-marked lines out of retrieved chunks."""
    chunks = _get_chunks_text(context)
    lines = chunks.split("\n")
    filtered = [
        line for line in lines
        if not any(m in line.lower() for m in ["draft", "unapproved", "pending review"])
    ]
    return "\n".join(filtered)


# ---------------------------------------------------------------------------
# Output rail actions
# ---------------------------------------------------------------------------

@action()
async def detect_legal_medical_advice(context: Optional[dict] = None) -> bool:
    """Pattern-matches unauthorized legal/medical advice in the bot's draft response."""
    response = _get_bot_text(context).lower()
    advice_markers = [
        "you should sue", "you have a right to", "legal claim", "lawsuit",
        "take this medication", "diagnosis", "prescription",
        "disability determination", "medical condition",
    ]
    return any(marker in response for marker in advice_markers)