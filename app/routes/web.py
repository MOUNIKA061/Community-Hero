import os

from flask import Blueprint, abort, jsonify, render_template, request

web_bp = Blueprint("web", __name__)


@web_bp.get("/")
def home():
    return render_template("index.html")


@web_bp.get("/report-issue")
def report_issue_page():
    return render_template("report_issue.html")


@web_bp.get("/track-issues")
def track_issues_page():
    return render_template("track_issues.html")


@web_bp.get("/about")
def about_page():
    return render_template("about.html")


@web_bp.get("/admin")
def admin_portal():
    from app.services.firestore_service import list_complaints

    try:
        complaints = list_complaints()
    except Exception:
        complaints = []
    summary = {
        "total": len(complaints),
        "reported": sum(1 for complaint in complaints if complaint.get("status") == "Reported"),
        "in_progress": sum(1 for complaint in complaints if complaint.get("status") == "In Progress"),
        "resolved": sum(1 for complaint in complaints if complaint.get("status") == "Resolved"),
    }

    categories = sorted({complaint.get("category", "Other") for complaint in complaints})
    severities = sorted({complaint.get("severity", "Medium") for complaint in complaints})
    statuses = ["Reported", "In Progress", "Resolved"]
    recent_complaints = complaints[:5]

    return render_template(
        "admin_dashboard.html",
        complaints=complaints,
        summary=summary,
        categories=categories,
        severities=severities,
        statuses=statuses,
        recent_complaints=recent_complaints,
        google_maps_api_key=os.getenv("GOOGLE_MAPS_API_KEY", ""),
        admin_mode=True,
    )


@web_bp.post("/admin/complaints/<complaint_id>/status")
def admin_update_status(complaint_id):
    payload = request.get_json(silent=True) or {}
    status = (payload.get("status") or "").strip()

    if not status:
        return jsonify({"error": "Status is required"}), 400

    try:
        from app.services.firestore_service import update_complaint_status

        updated_complaint = update_complaint_status(complaint_id, status)
        return jsonify(updated_complaint), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 500


@web_bp.get("/success/<complaint_id>")
def success_page(complaint_id):
    from app.services.firestore_service import get_complaint

    complaint = get_complaint(complaint_id)
    if not complaint:
        abort(404)
    return render_template("success.html", complaint=complaint)

