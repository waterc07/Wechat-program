from flask import Blueprint, request

from ..schemas.response import error_response
from ..schemas.response import success_response
from ..services.consultation_service import ConsultationService


consultations_bp = Blueprint("consultations", __name__, url_prefix="/api/consultations")
consultation_service = ConsultationService()


@consultations_bp.get("")
def list_consultations():
    user_id = request.args.get("user_id", type=int)
    if user_id is None:
        return error_response("user_id must be an integer.", code="VALIDATION_ERROR", status=400)

    return success_response(
        {
            "consultations": consultation_service.list_consultations(user_id),
        }
    )


@consultations_bp.get("/<int:consultation_id>/messages")
def get_consultation_messages(consultation_id):
    messages, consultation = consultation_service.list_messages(consultation_id)
    return success_response(
        {
            "consultation": consultation.to_dict(),
            "messages": messages,
        }
    )
