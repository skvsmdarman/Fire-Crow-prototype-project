import json
import logging
import urllib.request
from typing import Optional

from app.config import settings

logger = logging.getLogger("firecrow.safe_llm")

FEATURE_FLAG_SETTINGS = {
    "chat_assistant": "LLM_CHAT_ASSISTANT",
    "dashboard_insight": "LLM_DASHBOARD_INSIGHT",
    "attack_chain_naming": "LLM_ATTACK_CHAIN_NAMING",
    "pr_description": "LLM_PR_DESCRIPTION",
}

_feature_overrides: dict[str, bool] = {}


def enable_llm_feature(feature: str) -> None:
    if feature in FEATURE_FLAG_SETTINGS:
        _feature_overrides[feature] = True


def is_llm_enabled(feature: str) -> bool:
    if feature not in FEATURE_FLAG_SETTINGS:
        return False

    enabled = _feature_overrides.get(feature)
    if enabled is None:
        enabled = bool(getattr(settings, FEATURE_FLAG_SETTINGS[feature], False))

    return bool(enabled and settings.GEMINI_API_KEY and settings.GEMINI_MODEL)


def safe_llm_call(prompt: str, max_tokens: int = 50, temperature: float = 0.0) -> Optional[str]:
    if not settings.GEMINI_API_KEY or not settings.GEMINI_MODEL:
        return None

    # Check budget if we are inside a running job context
    from app.orchestrator.runtime_context import get_runtime_tracker, apply_runtime_updates
    tracker = get_runtime_tracker()
    remaining_budget = 5.0
    if tracker is not None:
        remaining_budget = tracker.state.get("budget_remaining_usd", 5.0)
        if remaining_budget <= 0.0:
            logger.warning("AI budget exhausted for this job. Skipping LLM call.")
            return None

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        },
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent"

    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"))
        req.add_header("Content-Type", "application/json")
        req.add_header("x-goog-api-key", settings.GEMINI_API_KEY)

        with urllib.request.urlopen(req, timeout=getattr(settings, "GEMINI_TIMEOUT_SECONDS", 30)) as response:
            body = json.loads(response.read().decode("utf-8"))
            text = body["candidates"][0]["content"]["parts"][0]["text"]
            
            # Decrement budget by estimated cost per call (e.g. $0.002)
            if tracker is not None:
                cost = 0.002
                new_budget = max(0.0, remaining_budget - cost)
                apply_runtime_updates({"budget_remaining_usd": new_budget})
                logger.info("Decremented job AI budget by $0.002. Remaining: $%.4f", new_budget)

            return text.strip() if text else None
    except Exception as exc:
        logger.warning("Safe LLM call failed: %s", exc)
        return None
