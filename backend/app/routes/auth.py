from flask import Blueprint

from ..schemas.request_validators import get_json_payload, validate_wx_login_payload
from ..schemas.response import success_response
from ..services.auth_service import AuthService


auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")
auth_service = AuthService()


@auth_bp.post("/wx-login")
def wx_login():
    payload = validate_wx_login_payload(get_json_payload())
    result = auth_service.login_with_wechat_stub(**payload)
    return success_response(result, message="Mock WeChat login succeeded.")

