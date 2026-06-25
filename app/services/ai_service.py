from typing import Optional


def classify_issue(media_url: str, description: Optional[str] = None) -> dict:
    """Stub AI classifier to be replaced with model/API inference."""
    return {
        "predicted_category": "pothole",
        "confidence": 0.91,
        "source_media": media_url,
        "description": description,
    }
