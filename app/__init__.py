import os
from logging.config import dictConfig
from typing import Optional

from dotenv import load_dotenv
from flask import Flask, render_template

from app.config.settings import config_by_name
from app.extensions import db, migrate
from app.routes import register_blueprints


def configure_logging() -> None:
    """Configure application logging."""
    dictConfig(
        {
            "version": 1,
            "formatters": {
                "default": {
                    "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
                }
            },
            "handlers": {
                "wsgi": {
                    "class": "logging.StreamHandler",
                    "stream": "ext://flask.logging.wsgi_errors_stream",
                    "formatter": "default",
                }
            },
            "root": {"level": "INFO", "handlers": ["wsgi"]},
        }
    )


def create_app(config_name: Optional[str] = None) -> Flask:
    """Application factory used by Flask runtime and WSGI servers."""
    load_dotenv()
    configure_logging()

    app = Flask(__name__, instance_relative_config=True)

    selected_config = config_name or os.getenv("FLASK_ENV", "development")
    app.config.from_object(config_by_name.get(selected_config, config_by_name["default"]))

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)

    register_blueprints(app)
    register_error_handlers(app)

    @app.get("/")
    def index():
        return render_template("index.html")

    return app


def register_error_handlers(app: Flask) -> None:
    """Centralized HTTP error handling."""

    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(error):
        return render_template("errors/500.html"), 500
