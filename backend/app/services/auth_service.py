import hashlib
import uuid

from ..extensions import db
from ..models import User


class AuthService:
    def login_with_wechat(
        self,
        *,
        code,
        mock_openid,
        nickname,
        cloud_openid="",
        cloud_appid="",
        cloud_unionid="",
    ):
        openid = cloud_openid or mock_openid or self._generate_mock_openid(code)
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
            "is_mock_login": not bool(cloud_openid),
            "wechat_appid": cloud_appid or None,
            "wechat_unionid": cloud_unionid or None,
        }

    def login_with_wechat_stub(self, *, code, mock_openid, nickname):
        return self.login_with_wechat(
            code=code,
            mock_openid=mock_openid,
            nickname=nickname,
        )

    @staticmethod
    def _generate_mock_openid(code):
        digest = hashlib.sha256(code.encode("utf-8")).hexdigest()
        return f"mock_{digest[:24]}"
