import json

from flask import Blueprint, Response, current_app, stream_with_context

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


def _build_sse_event(event, data):
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


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
        reply["content"],
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


@chat_bp.post("/chat/stream")
def chat_stream():
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
    consultation_id = consultation.id
    user_message_id = user_message.id
    disclaimer = get_disclaimer(payload["locale"])
    risk_result = risk_service.detect(payload["message"])
    llm_service = LLMService(current_app.config)

    if risk_result["risk_level"] == "high":
        consultation_for_save = consultation_service.get_consultation(consultation_id)
        assistant_text = f"{get_emergency_escalation_message(payload['locale'])}\n\n{disclaimer}"
        assistant_message = consultation_service.add_message(
            consultation_for_save,
            "assistant",
            assistant_text,
            risk_level="high",
        )
        assistant_message_payload = assistant_message.to_dict()
    else:
        history = [
            item.to_dict()
            for item in consultation.messages
            if item.id != user_message_id and item.role in {"user", "assistant"}
        ]
        prompt_messages = build_chat_messages(history, payload["message"], payload["locale"])

    @stream_with_context
    def generate():
        yield _build_sse_event(
            "meta",
            {
                "consultation_id": consultation_id,
                "created": created,
                "user_message_id": user_message_id,
            },
        )

        if risk_result["risk_level"] == "high":
            for chunk in llm_service._chunk_text_for_stream(assistant_text):
                yield _build_sse_event("delta", {"delta": chunk})

            yield _build_sse_event(
                "done",
                {
                    "consultation_id": consultation_id,
                    "created": created,
                    "assistant_message": assistant_message_payload,
                    "risk_level": "high",
                    "matched_keyword": risk_result["matched_keyword"],
                    "disclaimer": disclaimer,
                },
            )
            return

        final_reply = None
        try:
            for event in llm_service.stream_chat_reply(
                prompt_messages,
                {"latest_user_message": payload["message"], "locale": payload["locale"]},
            ):
                if event["type"] == "delta":
                    yield _build_sse_event("delta", {"delta": event["content"]})
                elif event["type"] == "complete":
                    final_reply = event
        except Exception as error:  # noqa: BLE001
            logger.exception(
                "Streaming chat failed unexpectedly. consultation_id=%s",
                consultation_id,
            )
            yield _build_sse_event(
                "error",
                {
                    "message": str(error) or "Streaming chat failed.",
                    "consultation_id": consultation_id,
                },
            )
            return

        if not final_reply or not final_reply.get("content"):
            logger.warning(
                "Streaming chat completed without content. consultation_id=%s",
                consultation_id,
            )
            yield _build_sse_event(
                "error",
                {
                    "message": "Streaming chat completed without content.",
                    "consultation_id": consultation_id,
                },
            )
            return

        consultation_for_save = consultation_service.get_consultation(consultation_id)
        assistant_message = consultation_service.add_message(
            consultation_for_save,
            "assistant",
            final_reply["content"],
            risk_level=final_reply["risk_level"],
        )

        yield _build_sse_event(
            "done",
            {
                "consultation_id": consultation_id,
                "created": created,
                "assistant_message": assistant_message.to_dict(),
                "risk_level": final_reply["risk_level"],
                "disclaimer": disclaimer,
            },
        )

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
