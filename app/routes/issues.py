import os
import uuid
import math
import logging
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request, url_for, current_app
from werkzeug.utils import secure_filename

issues_bp = Blueprint("issues", __name__)

logger = logging.getLogger(__name__)


def get_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    # Haversine formula
    R = 6371000  # Radius of Earth in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (math.sin(delta_phi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


@issues_bp.get("/")
def get_issues():
    try:
        from app.services.firestore_service import list_complaints
        return jsonify(list_complaints()), 200
    except Exception as e:
        logger.warning("Failed to fetch complaints from Firestore: %s", e)
        return jsonify([]), 200


@issues_bp.post("/")
def create_issue():
    # Support JSON payloads for forced resubmission bypass
    if request.is_json:
        payload = request.get_json()
        if payload.get("force") is True or payload.get("force") == "true":
            try:
                from app.services.firestore_service import save_complaint
                complaint_data = {
                    "media_url": payload.get("media_url"),
                    "media_type": payload.get("media_type"),
                    "category": payload.get("category"),
                    "description": payload.get("description") or "",
                    "severity": payload.get("severity", "Medium"),
                    "department": payload.get("department", "Other"),
                    "latitude": float(payload.get("latitude")),
                    "longitude": float(payload.get("longitude")),
                    "status": "Reported",
                    "support_count": 1,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                saved_complaint = save_complaint(complaint_data)
                return jsonify({
                    **saved_complaint,
                    "redirect_url": url_for("web.success_page", complaint_id=saved_complaint["id"]),
                }), 201
            except Exception as e:
                logger.error("Failed force save: %s", e)
                return jsonify({"error": str(e)}), 500

    if not request.content_type or "multipart/form-data" not in request.content_type:
        return jsonify({"error": "Content-type must be multipart/form-data"}), 400

    file = request.files.get("media")
    description = request.form.get("description", "")
    latitude = request.form.get("latitude")
    longitude = request.form.get("longitude")
    force_form = request.form.get("force") == "true"

    if not file or not latitude or not longitude:
        return jsonify({"error": "Media file, latitude, and longitude are required"}), 400

    try:
        file_bytes = file.read()
        file.seek(0)

        # Upload file (Firebase storage or local folder fallback)
        filename = secure_filename(file.filename) or "upload"
        ext = os.path.splitext(filename)[1]
        unique_filename = f"{uuid.uuid4().hex}{ext}"
        media_url = ""

        try:
            from app.services.firebase_service import get_storage_bucket
            bucket = get_storage_bucket()
            blob = bucket.blob(f"complaints/{unique_filename}")
            blob.upload_from_file(file, content_type=file.content_type)
            blob.make_public()
            media_url = blob.public_url
        except Exception as storage_err:
            logger.warning("Firebase storage failed: %s. Saving locally.", storage_err)
            local_upload_dir = os.path.join(current_app.root_path, "static", "uploads")
            os.makedirs(local_upload_dir, exist_ok=True)
            local_path = os.path.join(local_upload_dir, unique_filename)
            with open(local_path, "wb") as f:
                f.write(file_bytes)
            media_url = url_for("static", filename=f"uploads/{unique_filename}", _external=True)

        # Gemini AI Analysis
        ai_analysis = {}
        try:
            from app.services.gemini_service import analyze_media
            ai_analysis = analyze_media(
                file_bytes=file_bytes,
                mime_type=file.content_type,
                filename=filename
            )
        except Exception as gemini_err:
            logger.warning("Gemini AI analysis failed: %s. Using default category.", gemini_err)
            ai_analysis = {
                "category": "Other",
                "severity": "Medium",
                "department": "Other",
                "description": description or "Community reported issue.",
                "ai_recommendation": {
                    "recommended_action": "Inspect the reported issue and assign to the relevant department.",
                    "estimated_completion": "TBD",
                    "resources_needed": ["Municipal inspector"],
                    "risk_if_delayed": "May affect public safety or civic services.",
                    "priority_score": "Medium"
                }
            }

        category = ai_analysis.get("category", "Other")
        lat1 = float(latitude)
        lon1 = float(longitude)

        # Duplicate detection (only check if force is false)
        if not force_form:
            from app.services.firestore_service import list_complaints
            try:
                open_complaints = list_complaints()
            except Exception:
                open_complaints = []

            for complaint in open_complaints:
                if (complaint.get("category") == category and 
                        complaint.get("status") in ("Reported", "In Progress")):
                    lat2 = complaint.get("latitude")
                    lon2 = complaint.get("longitude")
                    if lat2 is not None and lon2 is not None:
                        dist = get_distance_meters(lat1, lon1, float(lat2), float(lon2))
                        if dist <= 100.0:  # 100 meters radius
                            return jsonify({
                                "duplicate_found": True,
                                "existing_complaint": complaint,
                                "distance_meters": round(dist, 1),
                                "category": category,
                                "severity": ai_analysis.get("severity", "Medium"),
                                "department": ai_analysis.get("department", "Other"),
                                "description": ai_analysis.get("description") or description or "",
                                "media_url": media_url,
                                "media_type": file.content_type,
                                "latitude": lat1,
                                "longitude": lon1
                            }), 200

        # Save complaint
        from app.services.firestore_service import save_complaint
        ai_rec = ai_analysis.get("ai_recommendation") or {}
        complaint_data = {
            "media_url": media_url,
            "media_type": file.content_type,
            "category": category,
            "description": ai_analysis.get("description") or description or "",
            "severity": ai_analysis.get("severity", "Medium"),
            "department": ai_analysis.get("department", "Other"),
            "latitude": lat1,
            "longitude": lon1,
            "status": "Reported",
            "support_count": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            # AI Municipal Officer recommendation fields
            "recommended_action": ai_rec.get("recommended_action", ""),
            "estimated_completion": ai_rec.get("estimated_completion", ""),
            "resources_needed": ai_rec.get("resources_needed", []),
            "risk_if_delayed": ai_rec.get("risk_if_delayed", ""),
            "ai_priority_score": ai_rec.get("priority_score", "Medium"),
        }

        saved_complaint = save_complaint(complaint_data)
        return jsonify({
            **saved_complaint,
            "redirect_url": url_for("web.success_page", complaint_id=saved_complaint["id"]),
        }), 201

    except Exception as e:
        logger.error("Create issue endpoint failed: %s", e)
        return jsonify({"error": str(e)}), 500


@issues_bp.post("/<complaint_id>/support")
def support_existing_complaint(complaint_id):
    try:
        from app.services.firestore_service import get_complaint, save_complaint
        complaint = get_complaint(complaint_id)
        if not complaint:
            return jsonify({"error": "Complaint not found"}), 404

        complaint["support_count"] = int(complaint.get("support_count", 1)) + 1
        save_complaint(complaint)

        return jsonify({
            "id": complaint_id,
            "support_count": complaint["support_count"],
            "redirect_url": url_for("web.success_page", complaint_id=complaint_id)
        }), 200
    except Exception as e:
        logger.error("Support complaint failed: %s", e)
        return jsonify({"error": str(e)}), 500



