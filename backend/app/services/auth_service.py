import hashlib
import uuid

from ..extensions import db
from ..models import User


class AuthService:
    def login_with_wechat_stub(self, *, code, mock_openid, nickname):
        openid = mock_openid or self._generate_mock_openid(code)
        user = User.query.filter_by(wx_openid=openid).first()

        if user is None:
            user = User(wx_openid=openid, nickname=nickname)
            db.session.add(user)
        else:
            user.nickname = nickname

        db.session.commit()

        return {
            "user": user.to_dict(),
            "session_token": str(uuid.uuid4()),
            "is_mock_login": True,
            "todo": "TODO: replace stubbed login with real WeChat code2Session flow.",
        }

    @staticmethod
    def _generate_mock_openid(code):
        digest = hashlib.sha256(code.encode("utf-8")).hexdigest()
        return f"mock_{digest[:24]}"

