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
    """Fail-closed result: BLOCK requests when scanning has errors to prevent data leakage.

    CRITICAL SECURITY DECISION: When Prisma AIRS API fails or is unavailable,
    we MUST block the request rather than allow it through. This prevents sensitive
    data from being processed without proper security scanning.
    """
    return {"safe": False, "risk_level": "high", "threats": ["SCANNING_UNAVAILABLE"], "confidence": 1.0, "error": error}


def is_prisma_airs_enabled() -> bool:
    """Scanning requires both an API key and an AI profile (name or id).

    Returns False if configuration is incomplete or invalid, which will trigger
    fail-closed behavior (blocking requests) instead of allowing data through.
    """
    has_key = bool(PRISMA_AIRS_API_KEY and PRISMA_AIRS_API_KEY.strip())
    has_profile = bool(PRISMA_AIRS_PROFILE_NAME or PRISMA_AIRS_PROFILE_ID)

    if not has_key or not has_profile:
        logger.warning("SECURITY: Prisma AIRS not fully configured - will block all requests")
        return False

    return True


def _ai_profile() -> dict:
    """Build AI profile for Prisma AIRS API.

    IMPORTANT: Prefer profile_name over profile_id because:
    - Profile names are stable and human-readable
    - Profile IDs can become invalid or mismatched
    - Using name is more reliable for scanning
    """
    # Use profile_name if available (more reliable)
    if PRISMA_AIRS_PROFILE_NAME:
        return {"profile_name": PRISMA_AIRS_PROFILE_NAME}
    # Fallback to profile_id (not recommended)
    elif PRISMA_AIRS_PROFILE_ID:
        return {"profile_id": PRISMA_AIRS_PROFILE_ID}
    # This shouldn't happen if is_prisma_airs_enabled() passed
    return {"profile_name": "Default"}


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
    """Map the Prisma AIRS response onto our internal result shape.

    SECURITY (defense-in-depth): we do NOT rely solely on the gateway's
    `action` field. A Palo Alto profile may be configured to only *log*
    (action="allow") detections like toxic_content or DLP rather than block
    them. Trusting `action` alone would let malicious content reach the model.

    We therefore treat content as UNSAFE if ANY of the following is true:
      - the gateway action is "block", OR
      - Prisma classified the content as "malicious", OR
      - any threat detection fired (prompt_detected / response_detected).

    This means our block decision is driven by what Prisma *detected*, not by
    how the remote profile's policy happens to be configured.
    """
    action = str(result.get("action", "allow")).lower()
    category = str(result.get("category", "benign")).lower()
    threats = _detected_threats(result)

    gateway_blocked = action == "block"
    is_malicious = category == "malicious"
    has_detections = len(threats) > 0

    unsafe = gateway_blocked or is_malicious or has_detections

    if unsafe:
        risk_level = "high" if (gateway_blocked or is_malicious) else "medium"
        logger.warning(
            "Prisma AIRS flagged content as UNSAFE (action=%s, category=%s, detections=%s) — blocking",
            action, category, threats,
        )
    else:
        risk_level = "low"
        logger.info("Prisma AIRS allowed content (category=%s, risk_level=%s)", category, risk_level)

    return {
        "safe": not unsafe,
        "risk_level": risk_level,
        "threats": threats,
        "confidence": 1.0,
        "error": None,
    }


def _scan(content: dict, model: str) -> dict:
    """Send a single scan request. `content` is {"prompt": ...} or {"response": ...}.

    CRITICAL: This function implements FAIL-CLOSED behavior:
    - If Prisma AIRS is not configured: BLOCK request
    - If API call fails: BLOCK request
    - If API returns error: BLOCK request
    - Only ALLOW if explicitly safe from successful scan

    This prevents data leakage when security scanning is unavailable.
    """
    if not is_prisma_airs_enabled():
        logger.critical("🚨 SECURITY: Prisma AIRS not fully configured - BLOCKING request to prevent data leakage")
        return _safe_result(error="Prisma AIRS not configured")

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
            logger.critical("🚨 SECURITY: Prisma AIRS API error HTTP %s - BLOCKING request to prevent data leakage", resp.status_code)
            return _safe_result(error=f"Prisma AIRS API error: {resp.status_code}")

        return _interpret(resp.json())

    except requests.Timeout:
        logger.critical("🚨 SECURITY: Prisma AIRS timeout - BLOCKING request to prevent data leakage")
        return _safe_result(error="Timeout")
    except requests.RequestException as exc:
        logger.critical("🚨 SECURITY: Prisma AIRS request error %s - BLOCKING request to prevent data leakage", type(exc).__name__)
        return _safe_result(error=type(exc).__name__)
    except Exception as exc:  # noqa: BLE001
        logger.critical("🚨 SECURITY: Unexpected Prisma AIRS error %s - BLOCKING request to prevent data leakage", type(exc).__name__)
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
