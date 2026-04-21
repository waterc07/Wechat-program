from datetime import datetime, timezone

from ..extensions import db


def utc_now():
    return datetime.now(timezone.utc)


class Consultation(db.Model):
    __tablename__ = "consultations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    status = db.Column(db.String(32), nullable=False, default="active")
    chief_complaint = db.Column(db.String(512), nullable=False, default="")
    risk_level = db.Column(db.String(32), nullable=False, default="low")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    user = db.relationship("User", back_populates="consultations")
    messages = db.relationship(
        "Message",
        back_populates="consultation",
        cascade="all, delete-orphan",
        order_by="Message.created_at.asc()",
        lazy=True,
    )
    reports = db.relationship(
        "Report",
        back_populates="consultation",
        cascade="all, delete-orphan",
        order_by="Report.created_at.desc()",
        lazy=True,
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "status": self.status,
            "chief_complaint": self.chief_complaint,
            "risk_level": self.risk_level,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

