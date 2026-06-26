import logging
import json
import os
from datetime import datetime, timezone, timedelta
from typing import Any, List, Optional

from app.services.firebase_service import get_firestore

logger = logging.getLogger(__name__)

ALLOWED_STATUSES = ("Reported", "In Progress", "Resolved")
JSON_DB_PATH = "instance/complaints_db.json"


def _load_json_db() -> list:
    if not os.path.exists(JSON_DB_PATH):
        os.makedirs(os.path.dirname(JSON_DB_PATH), exist_ok=True)
        now = datetime.now(timezone.utc)
        seeds = [
            {
                "id": "mock_pothole_1",
                "category": "Pothole",
                "description": "Deep pothole on the main street lane, causing cars to swerve suddenly.",
                "severity": "High",
                "department": "Road Maintenance",
                "latitude": 37.7749,
                "longitude": -122.4194,
                "status": "Reported",
                "support_count": 8,
                "created_at": (now - timedelta(minutes=15)).isoformat(),
                "media_url": "https://images.unsplash.com/photo-1515162305285-0293e4767cc2?auto=format&fit=crop&w=600&q=80",
                "media_type": "image/jpeg",
                "recommended_action": "Deploy a road crew to perform cold-mix asphalt patching. Clean the pothole, apply bonding agent, fill with asphalt, compact, and re-stripe the lane markings.",
                "estimated_completion": "2-3 hours",
                "resources_needed": ["2 Road Workers", "1 Asphalt Patcher Truck", "50kg Cold-mix Asphalt", "Traffic Cones"],
                "risk_if_delayed": "High risk of vehicle tyre damage, potential accidents as drivers swerve, possible injury to cyclists.",
                "ai_priority_score": "Critical"
            },
            {
                "id": "mock_streetlight_2",
                "category": "Damaged Streetlight",
                "description": "Flickering streetlight at the corner near the school crosswalk, unsafe at night.",
                "severity": "Medium",
                "department": "Electrical Department",
                "latitude": 37.7800,
                "longitude": -122.4250,
                "status": "In Progress",
                "support_count": 3,
                "created_at": (now - timedelta(hours=2)).isoformat(),
                "media_url": "https://images.unsplash.com/photo-1509024644558-2f56ce76c490?auto=format&fit=crop&w=600&q=80",
                "media_type": "image/jpeg",
                "recommended_action": "Dispatch an electrician to inspect the streetlight circuit. Replace the faulty ballast or LED driver. Test all connections before restoring power.",
                "estimated_completion": "1 working day",
                "resources_needed": ["1 Electrician", "1 Utility Van", "LED Streetlight Driver", "Safety Harness"],
                "risk_if_delayed": "Dangerous for pedestrians and school children crossing after dark. Increases road accident risk.",
                "ai_priority_score": "High"
            },
            {
                "id": "mock_garbage_3",
                "category": "Garbage Dump",
                "description": "Bulk garbage and plastics dumped on the sidewalk near the public park entrance.",
                "severity": "Low",
                "department": "Sanitation",
                "latitude": 37.7700,
                "longitude": -122.4100,
                "status": "Resolved",
                "support_count": 1,
                "created_at": (now - timedelta(days=1)).isoformat(),
                "media_url": "https://images.unsplash.com/photo-1611284446314-60a58ac0deb9?auto=format&fit=crop&w=600&q=80",
                "media_type": "image/jpeg",
                "recommended_action": "Send a sanitation crew to collect and dispose of the dumped garbage. Install a 'No Dumping' sign to deter repeat violations.",
                "estimated_completion": "3-5 hours",
                "resources_needed": ["2 Sanitation Workers", "1 Garbage Collection Vehicle", "Heavy-duty Waste Bags"],
                "risk_if_delayed": "Attracts pests, creates health hazard, and reduces public park accessibility.",
                "ai_priority_score": "Medium"
            }
        ]
        with open(JSON_DB_PATH, "w") as f:
            json.dump(seeds, f, indent=2)
        return seeds
    try:
        with open(JSON_DB_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return []


def _save_json_db(data: list):
    os.makedirs(os.path.dirname(JSON_DB_PATH), exist_ok=True)
    with open(JSON_DB_PATH, "w") as f:
        json.dump(data, f, indent=2)



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
    import uuid
    complaint_id = complaint_data.get("id")
    if not complaint_id:
        complaint_id = uuid.uuid4().hex

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

        normalized_data = _normalize_complaint_data(complaint_data, complaint_id)
            
        logger.info("Saving complaint to Firestore. Document ID: %s", normalized_data["id"])
        doc_ref.set(normalized_data)
        
        return normalized_data
    except Exception as e:
        logger.warning("Failed to save complaint to Firestore: %s. Using JSON fallback.", e)
        normalized_data = _normalize_complaint_data(complaint_data, complaint_id)
        db_list = _load_json_db()
        db_list = [c for c in db_list if c.get("id") != normalized_data["id"]]
        db_list.append(normalized_data)
        _save_json_db(db_list)
        return normalized_data



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
        logger.warning("Failed to retrieve complaint from Firestore: %s. Using JSON fallback.", e)
        db_list = _load_json_db()
        for c in db_list:
            if c.get("id") == complaint_id:
                return c
        return None



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
        logger.warning("Failed to list complaints from Firestore: %s. Using JSON fallback.", e)
        complaints = _load_json_db()
        complaints.sort(key=lambda complaint: complaint.get("created_at") or "", reverse=True)
        return complaints



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
        logger.warning("Failed to update complaint status in Firestore: %s. Using JSON fallback.", e)
        db_list = _load_json_db()
        found = False
        updated_c = None
        for c in db_list:
            if c.get("id") == complaint_id:
                c["status"] = status
                updated_c = c
                found = True
                break
        if found:
            _save_json_db(db_list)
            return updated_c
        raise ValueError("Complaint not found")

