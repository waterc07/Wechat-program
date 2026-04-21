import json
from datetime import datetime, timezone

from ..extensions import db


def utc_now():
    return datetime.now(timezone.utc)


class Report(db.Model):
    __tablename__ = "reports"

    id = db.Column(db.Integer, primary_key=True)
    consultation_id = db.Column(
        db.Integer,
        db.ForeignKey("consultations.id"),
        nullable=False,
        index=True,
    )
    symptoms_summary = db.Column(db.Text, nullable=False)
    possible_conditions = db.Column(db.Text, nullable=False)
    recommended_department = db.Column(db.String(128), nullable=False)
    urgency_level = db.Column(db.String(32), nullable=False)
    next_step_advice = db.Column(db.Text, nullable=False)
    disclaimer = db.Column(db.Text, nullable=False)
    raw_payload = db.Column(db.Text, nullable=False, default="{}")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    consultation = db.relationship("Consultation", back_populates="reports")

    def to_dict(self):
        return {
            "id": self.id,
            "consultation_id": self.consultation_id,
            "symptoms_summary": self.symptoms_summary,
            "possible_conditions": json.loads(self.possible_conditions or "[]"),
            "recommended_department": self.recommended_department,
            "urgency_level": self.urgency_level,
            "next_step_advice": self.next_step_advice,
            "disclaimer": self.disclaimer,
            "raw_payload": json.loads(self.raw_payload or "{}"),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

