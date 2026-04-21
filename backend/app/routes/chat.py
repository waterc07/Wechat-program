from flask import Blueprint, current_app

from ..constants import get_disclaimer, get_emergency_escalation_message
from ..schemas.request_validators import get_json_payload, validate_chat_payload
from ..schemas.response import success_response
from ..services.consultation_service import ConsultationService
from ..services.llm_service import LLMService, LLMServiceError
from ..services.prompt_builder import build_chat_messages
from ..services.risk_service import RiskService
from ..utils.logging import get_logger


chat_bp = Blueprint("chat", __name__, url_prefix="/api")
consultation_service = ConsultationService()
risk_service = RiskService()
logger = get_logger(__name__)


@chat_bp.post("/chat")
def chat():
    payload = validate_chat_payload(get_json_payload())
    consultation, created = consultation_service.get_or_create_consultation(
        payload["user_id"],
        payload["consultation_id"],
        chief_complaint=payload["message"],
    )
    user_message = consultation_service.add_message(
        consultation,
        "user",
        payload["message"],
        risk_level="low",
    )
    disclaimer = get_disclaimer(payload["locale"])

    risk_result = risk_service.detect(payload["message"])
    if risk_result["risk_level"] == "high":
        user_message.risk_level = "high"
        consultation.risk_level = "high"
        assistant_text = f"{get_emergency_escalation_message(payload['locale'])}\n\n{disclaimer}"
        assistant_message = consultation_service.add_message(
            consultation,
            "assistant",
            assistant_text,
            risk_level="high",
        )
        return success_response(
            {
                "consultation_id": consultation.id,
                "created": created,
                "assistant_message": assistant_message.to_dict(),
                "risk_level": "high",
                "matched_keyword": risk_result["matched_keyword"],
                "disclaimer": disclaimer,
            },
            message="Emergency risk detected.",
        )

    llm_service = LLMService(current_app.config)
    history = [
        item.to_dict()
        for item in consultation.messages
        if item.id != user_message.id and item.role in {"user", "assistant"}
    ]
    prompt_messages = build_chat_messages(history, payload["message"], payload["locale"])

    try:
        reply = llm_service.generate_chat_reply(
            prompt_messages,
            {"latest_user_message": payload["message"], "locale": payload["locale"]},
        )
    except LLMServiceError as error:
        logger.warning(
            "Chat provider call failed, using fallback. consultation_id=%s detail=%s",
            consultation.id,
            error.data,
        )
        reply = llm_service.build_chat_fallback(payload["message"], payload["locale"])

    assistant_message = consultation_service.add_message(
        consultation,
        "assistant",
        f"{reply['content']}\n\n{disclaimer}",
        risk_level=reply["risk_level"],
    )

    return success_response(
        {
            "consultation_id": consultation.id,
            "created": created,
            "assistant_message": assistant_message.to_dict(),
            "risk_level": reply["risk_level"],
            "disclaimer": disclaimer,
        },
        message="Chat reply generated.",
    )
