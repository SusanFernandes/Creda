"""Structured extraction from chat messages via Groq."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger("creda.extractors")


async def extract_financial_goal(message: str, llm: Any) -> dict[str, Any]:
    """
    Call Groq with a tight extraction prompt.
    Returns structured goal dict (possibly empty on failure).
    """
    prompt = f"""Extract financial goal details from this message.
Return ONLY valid JSON, no explanation, no markdown.
Schema: {{"amount": number_in_rupees_or_null,
          "years": integer_or_null,
          "goal_type": one_of_[fire,education,house,car,travel,wedding,emergency,other]_or_null,
          "monthly_sip": number_in_rupees_or_null,
          "fire_target_age": integer_or_null}}
Message: "{message}"
JSON:"""
    try:
        response = await llm.ainvoke(prompt)
        content = getattr(response, "content", None) or str(response)
        json_str = re.search(r"\{.*\}", content, re.DOTALL)
        if json_str:
            return json.loads(json_str.group())
    except Exception as e:
        logger.debug("extract_financial_goal failed: %s", e)
    return {}
