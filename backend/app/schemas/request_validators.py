from flask import request

from ..constants import normalize_locale
from ..utils.errors import ValidationError


def get_json_payload():
    payload = request.get_json(silent=True)
    if payload is None:
        raise ValidationError("Request body must be valid JSON.")
    return payload


def validate_wx_login_payload(payload):
    nickname = (payload.get("nickname") or "微信用户").strip()
    code = (payload.get("code") or "").strip()
    mock_openid = (payload.get("mock_openid") or "").strip()

    if not nickname:
        raise ValidationError("nickname is required.")

    if not code and not mock_openid:
        raise ValidationError("Either code or mock_openid is required.")

    return {"nickname": nickname[:128], "code": code, "mock_openid": mock_openid}


def validate_chat_payload(payload):
    user_id = payload.get("user_id")
    consultation_id = payload.get("consultation_id")
    message = (payload.get("message") or "").strip()
    locale = normalize_locale(payload.get("locale"))

    if not isinstance(user_id, int):
        raise ValidationError("user_id must be an integer.")
    if consultation_id is not None and not isinstance(consultation_id, int):
        raise ValidationError("consultation_id must be an integer when provided.")
    if not message:
        raise ValidationError("message is required.")
    if len(message) > 2000:
        raise ValidationError("message must be 2000 characters or fewer.")

    return {
        "user_id": user_id,
        "consultation_id": consultation_id,
        "message": message,
        "locale": locale,
    }


def validate_report_payload(payload):
    consultation_id = payload.get("consultation_id")
    locale = normalize_locale(payload.get("locale"))
    if not isinstance(consultation_id, int):
        raise ValidationError("consultation_id must be an integer.")
    return {"consultation_id": consultation_id, "locale": locale}
