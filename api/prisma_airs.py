"""Palo Alto Networks Prisma AIRS integration for AI prompt security scanning."""

import os
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

PRISMA_AIRS_API_URL = "https://service.api.aisecurity.paloaltonetworks.com"
PRISMA_AIRS_API_KEY = os.environ.get("PRISMA_AIRS_API_KEY")
PRISMA_AIRS_REGION = os.environ.get("PRISMA_AIRS_REGION", "americas")

# Risk levels
RISK_LEVELS = ["low", "medium", "high", "critical"]
RISK_LEVEL_VALUES = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def is_prisma_airs_enabled() -> bool:
    """Check if Prisma AIRS scanning is enabled."""
    return PRISMA_AIRS_API_KEY is not None and len(PRISMA_AIRS_API_KEY.strip()) > 0


def scan_prompt(prompt: str, model: str = "gemini-2.5-pro") -> dict:
    """Scan user prompt for security threats before sending to LLM.

    Args:
        prompt: User's input prompt
        model: LLM model name for context

    Returns:
        {
            "safe": bool,
            "risk_level": "low|medium|high|critical",
            "threats": list[str],
            "confidence": float,
            "error": str or None
        }
    """
    if not is_prisma_airs_enabled():
        logger.warning("Prisma AIRS is not configured. Skipping prompt scan.")
        return {"safe": True, "risk_level": "low", "threats": [], "confidence": 1.0, "error": None}

    try:
        headers = {
            "x-pan-token": PRISMA_AIRS_API_KEY,
            "Content-Type": "application/json",
        }

        payload = {
            "metadata": {
                "type": "prompt",
                "model": model,
                "region": PRISMA_AIRS_REGION,
            },
            "contents": {"prompt": prompt},
        }

        response = requests.post(
            f"{PRISMA_AIRS_API_URL}/scan",
            json=payload,
            headers=headers,
            timeout=5,
        )

        if response.status_code != 200:
            error_msg = f"Prisma AIRS API error: {response.status_code}"
            # Log status code only, never log response body (could contain API key)
            logger.error(f"{error_msg} from Palo Alto API")
            # On error, default to allowing the request (fail-open for availability)
            return {"safe": True, "risk_level": "low", "threats": [], "confidence": 0.0, "error": error_msg}

        result = response.json()

        # Extract risk level
        risk_level = result.get("risk_level", "low").lower()
        if risk_level not in RISK_LEVELS:
            risk_level = "low"

        # Check if safe (not high or critical)
        is_safe = RISK_LEVEL_VALUES.get(risk_level, 0) < 2

        # Extract threats
        threats = result.get("threats_detected", [])
        confidence = result.get("confidence", 0.0)

        scan_result = {
            "safe": is_safe,
            "risk_level": risk_level,
            "threats": threats,
            "confidence": confidence,
            "error": None,
        }

        if not is_safe:
            logger.warning(f"Prompt security threat detected: {risk_level} - Threats: {threats}")

        return scan_result

    except requests.Timeout:
        logger.error("Prisma AIRS API timeout (5s). Allowing request to proceed.")
        return {"safe": True, "risk_level": "low", "threats": [], "confidence": 0.0, "error": "Timeout"}
    except requests.RequestException as e:
        logger.error(f"Prisma AIRS API error: {str(e)}. Allowing request to proceed.")
        return {"safe": True, "risk_level": "low", "threats": [], "confidence": 0.0, "error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error in Prisma AIRS scanning: {str(e)}")
        return {"safe": True, "risk_level": "low", "threats": [], "confidence": 0.0, "error": str(e)}


def scan_response(response_text: str, model: str = "gemini-2.5-pro") -> dict:
    """Scan LLM response for data leakage or malicious content.

    Args:
        response_text: LLM's response output
        model: LLM model name for context

    Returns:
        {
            "safe": bool,
            "risk_level": "low|medium|high|critical",
            "threats": list[str],
            "confidence": float,
            "error": str or None
        }
    """
    if not is_prisma_airs_enabled():
        return {"safe": True, "risk_level": "low", "threats": [], "confidence": 1.0, "error": None}

    try:
        headers = {
            "x-pan-token": PRISMA_AIRS_API_KEY,
            "Content-Type": "application/json",
        }

        payload = {
            "metadata": {
                "type": "response",
                "model": model,
                "region": PRISMA_AIRS_REGION,
            },
            "contents": {"response": response_text},
        }

        response = requests.post(
            f"{PRISMA_AIRS_API_URL}/scan",
            json=payload,
            headers=headers,
            timeout=5,
        )

        if response.status_code != 200:
            error_msg = f"Prisma AIRS API error: {response.status_code}"
            # Log status code only, never log response body (could contain API key)
            logger.error(f"{error_msg} from Palo Alto API")
            # Fail-open: allow response if scanning fails
            return {"safe": True, "risk_level": "low", "threats": [], "confidence": 0.0, "error": error_msg}

        result = response.json()
        risk_level = result.get("risk_level", "low").lower()
        if risk_level not in RISK_LEVELS:
            risk_level = "low"

        is_safe = RISK_LEVEL_VALUES.get(risk_level, 0) < 2
        threats = result.get("threats_detected", [])
        confidence = result.get("confidence", 0.0)

        if not is_safe:
            logger.warning(f"Response security threat detected: {risk_level} - Threats: {threats}")

        return {
            "safe": is_safe,
            "risk_level": risk_level,
            "threats": threats,
            "confidence": confidence,
            "error": None,
        }

    except requests.Timeout:
        logger.error("Prisma AIRS response scan timeout. Allowing response.")
        return {"safe": True, "risk_level": "low", "threats": [], "confidence": 0.0, "error": "Timeout"}
    except requests.RequestException as e:
        logger.error(f"Prisma AIRS API error during response scan: {str(e)}")
        return {"safe": True, "risk_level": "low", "threats": [], "confidence": 0.0, "error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error scanning response: {str(e)}")
        return {"safe": True, "risk_level": "low", "threats": [], "confidence": 0.0, "error": str(e)}
