from flask import Blueprint, jsonify, request

from app.services.issue_service import list_issues, submit_issue

issues_bp = Blueprint("issues", __name__)


@issues_bp.get("/")
def get_issues():
    return jsonify(list_issues()), 200


@issues_bp.post("/")
def create_issue():
    payload = request.get_json(silent=True) or {}
    issue = submit_issue(payload)
    return jsonify(issue), 201
