from datetime import datetime, timezone
from typing import Dict, List

from app.services.ai_service import classify_issue

_ISSUES: List[Dict] = []


def list_issues() -> List[Dict]:
    return _ISSUES


def submit_issue(payload: dict) -> dict:
    media_url = payload.get("media_url", "")
    description = payload.get("description")

    ai_result = classify_issue(media_url=media_url, description=description)

    issue = {
        "id": len(_ISSUES) + 1,
        "description": description,
        "media_url": media_url,
        "location": payload.get("location"),
        "status": "reported",
        "ai_analysis": ai_result,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _ISSUES.append(issue)
    return issue
