from datetime import datetime, timezone

from ..extensions import db


def utc_now():
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    wx_openid = db.Column(db.String(128), unique=True, nullable=False, index=True)
    nickname = db.Column(db.String(128), nullable=False, default="微信用户")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    consultations = db.relationship("Consultation", back_populates="user", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "wx_openid": self.wx_openid,
            "nickname": self.nickname,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

