from datetime import datetime, timezone

from ..extensions import db


def utc_now():
    return datetime.now(timezone.utc)


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    consultation_id = db.Column(
        db.Integer,
        db.ForeignKey("consultations.id"),
        nullable=False,
        index=True,
    )
    role = db.Column(db.String(32), nullable=False)
    content = db.Column(db.Text, nullable=False)
    risk_level = db.Column(db.String(32), nullable=False, default="low")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    consultation = db.relationship("Consultation", back_populates="messages")

    def to_dict(self):
        return {
            "id": self.id,
            "consultation_id": self.consultation_id,
            "role": self.role,
            "content": self.content,
            "risk_level": self.risk_level,
            "created_at": self.created_at.isoformat(),
        }

