from flask import Flask

from app.routes.health import health_bp
from app.routes.issues import issues_bp


def register_blueprints(app: Flask) -> None:
    """Register all application blueprints in one place."""
    app.register_blueprint(health_bp, url_prefix="/api/v1")
    app.register_blueprint(issues_bp, url_prefix="/api/v1/issues")
