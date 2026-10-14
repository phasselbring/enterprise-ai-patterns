"""Normalize tool traces; never log credentials or raw sensitive payloads."""
from typing import Any

def summarize_trace(calls: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [{"name": str(c.get("name", "")), "status": str(c.get("status", "unknown"))} for c in calls]
