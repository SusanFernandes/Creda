"""Standard agent response envelope (Part 8)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def wrap_agent_response(
    agent: str,
    status: str,
    data_quality: str,
    assumptions_used: dict[str, Any],
    output: dict[str, Any],
) -> dict[str, Any]:
    return {
        "agent": agent,
        "status": status,
        "data_quality": data_quality,
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "assumptions_used": assumptions_used,
        "output": output,
    }
