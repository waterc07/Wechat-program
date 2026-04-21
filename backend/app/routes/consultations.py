from flask import Blueprint

from ..schemas.response import success_response
from ..services.consultation_service import ConsultationService


consultations_bp = Blueprint("consultations", __name__, url_prefix="/api/consultations")
consultation_service = ConsultationService()


@consultations_bp.get("/<int:consultation_id>/messages")
def get_consultation_messages(consultation_id):
    messages, consultation = consultation_service.list_messages(consultation_id)
    return success_response(
        {
            "consultation": consultation.to_dict(),
            "messages": messages,
        }
    )

