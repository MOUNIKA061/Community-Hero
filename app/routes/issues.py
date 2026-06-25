from flask import Blueprint, jsonify, request, url_for

issues_bp = Blueprint("issues", __name__)


@issues_bp.get("/")
def get_issues():
    try:
        from app.services.firestore_service import list_complaints
        return jsonify(list_complaints()), 200
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Failed to fetch complaints from Firestore: %s", e)
        return jsonify([]), 200


@issues_bp.post("/")
def create_issue():
    if not request.content_type or "multipart/form-data" not in request.content_type:
        return jsonify({"error": "Content-type must be multipart/form-data"}), 400

    file = request.files.get("media")
    description = request.form.get("description", "")
    latitude = request.form.get("latitude")
    longitude = request.form.get("longitude")

    if not file or not latitude or not longitude:
        return jsonify({"error": "Media file, latitude, and longitude are required"}), 400

    try:
        # 1. Read bytes for Gemini
        file_bytes = file.read()
        file.seek(0)

        # 2. Upload to Firebase Storage
        import uuid
        import os
        from werkzeug.utils import secure_filename
        from app.services.firebase_service import get_storage_bucket

        filename = secure_filename(file.filename)
        if not filename:
            filename = "upload"
        ext = os.path.splitext(filename)[1]
        unique_filename = f"{uuid.uuid4().hex}{ext}"

        bucket = get_storage_bucket()
        blob = bucket.blob(f"complaints/{unique_filename}")
        blob.upload_from_file(file, content_type=file.content_type)
        blob.make_public()
        media_url = blob.public_url

        # 3. Analyze media using Gemini AI
        from app.services.gemini_service import analyze_media
        ai_analysis = analyze_media(
            file_bytes=file_bytes,
            mime_type=file.content_type,
            filename=filename
        )

        # 4. Save to Firestore
        from app.services.firestore_service import save_complaint
        from datetime import datetime, timezone

        complaint_data = {
            "media_url": media_url,
            "media_type": file.content_type,
            "category": ai_analysis.get("category", "Other"),
            "description": ai_analysis.get("description") or description or "",
            "severity": ai_analysis.get("severity", "Medium"),
            "department": ai_analysis.get("department", "Other"),
            "latitude": float(latitude),
            "longitude": float(longitude),
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
        import logging
        logging.getLogger(__name__).error("Pipeline processing failed: %s", e)
        return jsonify({"error": str(e)}), 500


