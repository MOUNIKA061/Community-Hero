# Community Hero AI

Community Hero AI is a production-ready Flask starter for an AI-powered civic issue reporting platform.

## Features
- Flask application factory pattern
- Blueprint-based route modularity
- Config management with `.env` support
- Service layer separation
- SQLAlchemy + Flask-Migrate integration
- Starter templates and static assets

## Project Structure

```text
Community Hero AI/
|-- app/
|   |-- __init__.py
|   |-- extensions.py
|   |-- config/
|   |   |-- __init__.py
|   |   `-- settings.py
|   |-- models/
|   |   |-- __init__.py
|   |   `-- issue.py
|   |-- routes/
|   |   |-- __init__.py
|   |   |-- health.py
|   |   `-- issues.py
|   |-- services/
|   |   |-- __init__.py
|   |   |-- ai_service.py
|   |   `-- issue_service.py
|   |-- static/
|   |   |-- css/
|   |   |   `-- styles.css
|   |   `-- js/
|   |       `-- main.js
|   `-- templates/
|       |-- base.html
|       |-- index.html
|       `-- errors/
|           |-- 404.html
|           `-- 500.html
|-- tests/
|   |-- __init__.py
|   `-- test_health.py
|-- .env.example
|-- .gitignore
|-- requirements.txt
|-- run.py
`-- wsgi.py
```

## Quick Start

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and update values.
4. Start the app:

```bash
python run.py
```

5. Verify health endpoint:

```bash
GET /api/v1/health
```

## Production Run

```bash
gunicorn wsgi:app
```
