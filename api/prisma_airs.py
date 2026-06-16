"""Palo Alto Networks Prisma AIRS integration for AI prompt/response scanning.

Uses the synchronous scan API:
  POST https://service.api.aisecurity.paloaltonetworks.com/v1/scan/sync/request
  Header: x-pan-token: <API key>
  Body:   { "ai_profile": {"profile_name": "..."},
            "metadata": {...},
            "contents": [{"prompt": "..."}] }

A valid AI security profile (configured in the Palo Alto tenant) is required.
Set PRISMA_AIRS_PROFILE_NAME (or PRISMA_AIRS_PROFILE_ID) in the environment.
"""

import os
import logging
import requests

logger = logging.getLogger(__name__)

PRISMA_AIRS_API_KEY = os.environ.get("PRISMA_AIRS_API_KEY")
PRISMA_AIRS_REGION = os.environ.get("PRISMA_AIRS_REGION", "americas")
PRISMA_AIRS_PROFILE_NAME = os.environ.get("PRISMA_AIRS_PROFILE_NAME")
PRISMA_AIRS_PROFILE_ID = os.environ.get("PRISMA_AIRS_PROFILE_ID")

# Same endpoint for all regions; API keys are region-locked server-side.
PRISMA_AIRS_API_URL = "https://service.api.aisecurity.paloaltonetworks.com"
SCAN_PATH = "/v1/scan/sync/request"

# Timeout (connect, read) — keep short so a slow scanner doesn't block the chat
_TIMEOUT = (2, 5)


def _safe_result(error: str | None = None) -> dict:
    """Fail-open result: allow the request through when scanning is unavailable."""
    return {"safe": True, "risk_level": "low", "threats": [], "confidence": 1.0, "error": error}


def is_prisma_airs_enabled() -> bool:
    """Scanning requires both an API key and an AI profile (name or id)."""
    has_key = bool(PRISMA_AIRS_API_KEY and PRISMA_AIRS_API_KEY.strip())
    has_profile = bool(PRISMA_AIRS_PROFILE_NAME or PRISMA_AIRS_PROFILE_ID)
    return has_key and has_profile


def _ai_profile() -> dict:
    if PRISMA_AIRS_PROFILE_ID:
        return {"profile_id": PRISMA_AIRS_PROFILE_ID}
    return {"profile_name": PRISMA_AIRS_PROFILE_NAME}


def _detected_threats(result: dict) -> list[str]:
    """Collect the names of triggered detections from prompt/response sections."""
    threats: list[str] = []
    for section in ("prompt_detected", "response_detected"):
        detected = result.get(section) or {}
        for name, hit in detected.items():
            if hit:
                threats.append(name)
    return threats


def _interpret(result: dict) -> dict:
    """Map the Prisma AIRS response onto our internal result shape."""
    action = str(result.get("action", "allow")).lower()
    category = str(result.get("category", "benign")).lower()
    threats = _detected_threats(result)

    blocked = action == "block"
    risk_level = "high" if blocked else ("medium" if category == "malicious" else "low")

    if blocked:
        logger.warning("Prisma AIRS blocked content (category=%s, detections=%s)", category, threats)

    return {
        "safe": not blocked,
        "risk_level": risk_level,
        "threats": threats,
        "confidence": 1.0,
        "error": None,
    }


def _scan(content: dict, model: str) -> dict:
    """Send a single scan request. `content` is {"prompt": ...} or {"response": ...}."""
    if not is_prisma_airs_enabled():
        logger.warning("Prisma AIRS not fully configured (API key + profile required). Skipping scan.")
        return _safe_result()

    try:
        headers = {"x-pan-token": PRISMA_AIRS_API_KEY, "Content-Type": "application/json"}
        payload = {
            "ai_profile": _ai_profile(),
            "metadata": {
                "app_name": "sql-agent",
                "app_user": "chatbot",
                "ai_model": model,
            },
            "contents": [content],
        }

        resp = requests.post(
            f"{PRISMA_AIRS_API_URL}{SCAN_PATH}",
            json=payload,
            headers=headers,
            timeout=_TIMEOUT,
        )

        if resp.status_code != 200:
            # Never log the response body (avoid leaking sensitive content/keys)
            logger.error("Prisma AIRS API error: HTTP %s from Palo Alto API", resp.status_code)
            return _safe_result(error=f"Prisma AIRS API error: {resp.status_code}")

        return _interpret(resp.json())

    except requests.Timeout:
        logger.error("Prisma AIRS timeout. Allowing request to proceed.")
        return _safe_result(error="Timeout")
    except requests.RequestException as exc:
        logger.error("Prisma AIRS request error: %s. Allowing request to proceed.", type(exc).__name__)
        return _safe_result(error=type(exc).__name__)
    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected Prisma AIRS error: %s", type(exc).__name__)
        return _safe_result(error=type(exc).__name__)


def scan_prompt(prompt: str, model: str = "gemini-2.5-pro") -> dict:
    """Scan a user prompt before it reaches the LLM.

    Returns: {"safe": bool, "risk_level": str, "threats": list[str],
              "confidence": float, "error": str | None}
    """
    return _scan({"prompt": prompt}, model)


def scan_response(response_text: str, model: str = "gemini-2.5-pro") -> dict:
    """Scan an LLM response before it is returned to the user."""
    return _scan({"response": response_text}, model)
