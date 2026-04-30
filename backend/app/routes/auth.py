from flask import Blueprint, request

from ..schemas.request_validators import get_json_payload, validate_wx_login_payload
from ..schemas.response import success_response
from ..services.auth_service import AuthService


auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")
auth_service = AuthService()


def _get_cloud_header(*names):
    for name in names:
        value = (request.headers.get(name) or "").strip()
        if value:
            return value
    return ""


@auth_bp.post("/wx-login")
def wx_login():
    payload = validate_wx_login_payload(get_json_payload())
    result = auth_service.login_with_wechat(
        **payload,
        cloud_openid=_get_cloud_header("X-WX-OPENID", "X-WX-FROM-OPENID"),
        cloud_appid=_get_cloud_header("X-WX-APPID", "X-WX-FROM-APPID"),
        cloud_unionid=_get_cloud_header("X-WX-UNIONID", "X-WX-FROM-UNIONID"),
    )
    return success_response(result, message="WeChat login succeeded.")
