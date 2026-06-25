import logging
from datetime import datetime
from typing import Any, List, Optional

from app.services.firebase_service import get_firestore

logger = logging.getLogger(__name__)

ALLOWED_STATUSES = ("Reported", "In Progress", "Resolved")


def _serialize_value(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _safe_int(value, default: int = 1) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_complaint_data(complaint_data: dict, complaint_id: str) -> dict:
    normalized = {
        "id": complaint_id,
        "media_url": complaint_data.get("media_url", ""),
        "media_type": complaint_data.get("media_type", ""),
        "category": complaint_data.get("category", "Other"),
        "description": complaint_data.get("description", ""),
        "severity": complaint_data.get("severity", "Medium"),
        "department": complaint_data.get("department", "Other"),
        "latitude": complaint_data.get("latitude"),
        "longitude": complaint_data.get("longitude"),
        "status": complaint_data.get("status", "Reported"),
        "support_count": _safe_int(complaint_data.get("support_count", 1), default=1),
        "created_at": complaint_data.get("created_at") or datetime.utcnow().isoformat(),
    }

    # Preserve any additional fields without breaking Firestore serialization.
    for key, value in complaint_data.items():
        if key not in normalized:
            normalized[key] = _serialize_value(value)

    for key, value in list(normalized.items()):
        normalized[key] = _serialize_value(value)

    return normalized


def _complaint_from_document(document: Any) -> dict:
    complaint_id = str(getattr(document, "id", ""))
    to_dict = getattr(document, "to_dict", lambda: {})
    complaint = to_dict() or {}
    return _normalize_complaint_data(complaint, complaint_id)

def save_complaint(complaint_data: dict) -> dict:
    """
    Saves a complaint dictionary to the Firestore database under the 'complaints' collection.
    Automatically generates and assigns a unique document ID if not already provided.
    """
    try:
        db = get_firestore()
        collection_ref = db.collection("complaints")
        
        # Generate a unique document ID using Firestore if not present
        if not complaint_data.get("id"):
            doc_ref = collection_ref.document()
            complaint_id = doc_ref.id
        else:
            complaint_id = str(complaint_data["id"])
            doc_ref = collection_ref.document(complaint_id)

        complaint_data = _normalize_complaint_data(complaint_data, complaint_id)
            
        logger.info("Saving complaint to Firestore. Document ID: %s", complaint_data["id"])
        doc_ref.set(complaint_data)
        
        return complaint_data
    except Exception as e:
        logger.error("Failed to save complaint to Firestore: %s", e)
        raise RuntimeError(f"Failed to save complaint to Firestore: {e}")


def get_complaint(complaint_id: str) -> Optional[dict]:
    """
    Retrieves a complaint from Firestore by its ID.
    Returns None if the document does not exist.
    """
    try:
        db = get_firestore()
        doc_ref = db.collection("complaints").document(complaint_id)
        doc = doc_ref.get()
        
        if bool(getattr(doc, "exists", False)):
            return _complaint_from_document(doc)
        return None
    except Exception as e:
        logger.error("Failed to retrieve complaint from Firestore: %s", e)
        raise RuntimeError(f"Failed to retrieve complaint from Firestore: {e}")


def list_complaints() -> List[dict]:
    """
    Returns all complaints from Firestore as normalized dictionaries.
    """
    try:
        db = get_firestore()
        docs = db.collection("complaints").stream()
        complaints = [_complaint_from_document(doc) for doc in docs]
        complaints.sort(key=lambda complaint: complaint.get("created_at") or "", reverse=True)
        return complaints
    except Exception as e:
        logger.error("Failed to list complaints from Firestore: %s", e)
        raise RuntimeError(f"Failed to list complaints from Firestore: {e}")


def update_complaint_status(complaint_id: str, status: str) -> dict:
    """
    Updates the complaint status in Firestore and returns the normalized document.
    """
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"Invalid status: {status}")

    try:
        db = get_firestore()
        doc_ref = db.collection("complaints").document(complaint_id)
        doc = doc_ref.get()

        if not bool(getattr(doc, "exists", False)):
            raise ValueError("Complaint not found")

        doc_ref.update({"status": status})
        updated_doc = doc_ref.get()
        return _complaint_from_document(updated_doc)
    except Exception as e:
        logger.error("Failed to update complaint status in Firestore: %s", e)
        raise RuntimeError(f"Failed to update complaint status in Firestore: {e}")
