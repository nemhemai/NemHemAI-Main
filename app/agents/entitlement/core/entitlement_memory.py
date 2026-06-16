from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MEMORY_PATH = Path("storage") / "entitlement_memory.jsonl"


def remember_entitlement_result(result: dict[str, Any]) -> None:
    """
    Lightweight local memory log for orchestration/debugging.

    This intentionally never raises to the caller; memory should not break a
    citizen-facing entitlement determination.
    """
    try:
        MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": result.get("agent", "entitlement"),
            "citizen_id": result.get("citizen_id"),
            "user_id": result.get("user_id"),
            "status": result.get("status"),
            "profile": result.get("extracted_profile", {}),
            "scheme_matches": result.get("scheme_matches", []),
            "verdict": (result.get("determination") or {}).get("verdict"),
        }
        with MEMORY_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=True) + "\n")
    except Exception:
        return
