from app.extensions import db
from app.models import TimestampMixin


class Issue(TimestampMixin, db.Model):
    __tablename__ = "issues"

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(80), nullable=False)
    description = db.Column(db.Text, nullable=True)
    media_url = db.Column(db.String(500), nullable=False)
    location = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(40), nullable=False, default="reported")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "category": self.category,
            "description": self.description,
            "media_url": self.media_url,
            "location": self.location,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
