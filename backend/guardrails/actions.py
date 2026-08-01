# backend/guardrails/actions.py

import hashlib
import re
from datetime import datetime
from typing import Optional

from nemoguardrails.actions import action
from app.core.logging import get_logger

logger = get_logger("actions")


def _get_user_text(context: Optional[dict]) -> str:
    if not context:
        return ""
    return (context.get("last_user_message") or context.get("user_message") or "")


def _get_bot_text(context: Optional[dict]) -> str:
    if not context:
        return ""
    return (context.get("last_bot_message") or context.get("bot_message") or "")


def _get_chunks_text(context: Optional[dict]) -> str:
    if not context:
        return ""
    return context.get("relevant_chunks") or ""


@action()
async def self_check_input(context: Optional[dict] = None, llm=None) -> bool:
    try:
        user_input = _get_user_text(context)
        logger.info(f"self_check_input | checking: '{user_input[:80]}'")
        return True  # placeholder — real LLM check pending
    except Exception:
        logger.exception("self_check_input | FAILED — defaulting to allow")
        return True


@action()
async def detect_harassment_intent(context: Optional[dict] = None) -> bool:
    try:
        user_input = _get_user_text(context).lower()
        harassment_keywords = [
            "harassment", "harassed", "inappropriate", "uncomfortable",
            "discrimination", "retaliation", "hostile", "bullying",
            "sexual", "abuse", "threatened", "intimidated",
        ]
        result = any(kw in user_input for kw in harassment_keywords)
        if result:
            logger.warning(f"detect_harassment_intent | TRIGGERED: '{user_input[:80]}'")
        return result
    except Exception:
        logger.exception("detect_harassment_intent | FAILED — defaulting to False")
        return False


@action()
async def create_anonymous_ticket(type: str = "general", context: Optional[dict] = None) -> str:
    try:
        session_id = context.get("session_id", "unknown") if context else "unknown"
        ticket_id = (
            f"HR-{hashlib.sha256(session_id.encode()).hexdigest()[:8].upper()}"
            f"-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        )
        logger.info(f"create_anonymous_ticket | created {ticket_id} (type={type})")
        return ticket_id
    except Exception:
        logger.exception("create_anonymous_ticket | FAILED")
        return "HR-ERROR-TICKET"


@action()
async def detect_pii_in_chunks(context: Optional[dict] = None) -> bool:
    try:
        chunks = _get_chunks_text(context).lower()
        markers = ["ssn", "social security", "salary:", "compensation:", "employee id:", "dob:", "date of birth"]
        result = any(m in chunks for m in markers)
        if result:
            logger.warning("detect_pii_in_chunks | PII marker found in retrieved chunks")
        return result
    except Exception:
        logger.exception("detect_pii_in_chunks | FAILED — defaulting to False")
        return False


@action()
async def mask_pii_in_chunks(context: Optional[dict] = None) -> str:
    try:
        chunks = _get_chunks_text(context)
        chunks = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[SSN REDACTED]", chunks)
        chunks = re.sub(r"\$\d{1,3}(,\d{3})+(\.\d{2})?", "[COMPENSATION REDACTED]", chunks)
        chunks = re.sub(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b", "[CARD REDACTED]", chunks)
        return chunks
    except Exception:
        logger.exception("mask_pii_in_chunks | FAILED — returning empty string")
        return ""


@action()
async def detect_draft_policy(context: Optional[dict] = None) -> bool:
    try:
        chunks = _get_chunks_text(context).lower()
        markers = ["draft", "unapproved", "pending review", "not yet effective", "proposed"]
        result = any(m in chunks for m in markers)
        if result:
            logger.warning("detect_draft_policy | draft content found in retrieved chunks")
        return result
    except Exception:
        logger.exception("detect_draft_policy | FAILED — defaulting to False")
        return False


@action()
async def filter_draft_chunks(context: Optional[dict] = None) -> str:
    try:
        chunks = _get_chunks_text(context)
        lines = chunks.split("\n")
        filtered = [l for l in lines if not any(m in l.lower() for m in ["draft", "unapproved", "pending review"])]
        return "\n".join(filtered)
    except Exception:
        logger.exception("filter_draft_chunks | FAILED — returning original chunks")
        return _get_chunks_text(context)


@action()
async def detect_legal_medical_advice(context: Optional[dict] = None) -> bool:
    try:
        response = _get_bot_text(context).lower()
        markers = ["you should sue", "you have a right to", "legal claim", "lawsuit",
                   "take this medication", "diagnosis", "prescription",
                   "disability determination", "medical condition"]
        result = any(m in response for m in markers)
        if result:
            logger.warning("detect_legal_medical_advice | advice marker found in bot response")
        return result
    except Exception:
        logger.exception("detect_legal_medical_advice | FAILED — defaulting to False")
        return False