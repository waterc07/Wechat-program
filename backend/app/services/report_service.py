import json

from ..constants import DISCLAIMER_TEXT
from ..extensions import db
from ..models import Report
from ..utils.logging import get_logger
from .consultation_service import ConsultationService
from .llm_service import LLMService, LLMServiceError
from .prompt_builder import build_report_messages


logger = get_logger(__name__)


class ReportService:
    def __init__(self, config):
        self.config = config
        self.consultation_service = ConsultationService()
        self.llm_service = LLMService(config)

    def generate_report(self, consultation_id):
        consultation = self.consultation_service.get_consultation(consultation_id)
        conversation_messages = [message.to_dict() for message in consultation.messages]
        conversation_text = "\n".join(
            [f"{item['role']}: {item['content']}" for item in conversation_messages]
        )
        prompt_messages = build_report_messages(conversation_messages)

        try:
            report_payload = self.llm_service.generate_report(
                prompt_messages,
                {"conversation_text": conversation_text},
            )
        except LLMServiceError as error:
            logger.warning(
                "Report provider call failed, using fallback. consultation_id=%s detail=%s",
                consultation.id,
                error.data,
            )
            report_payload = self.llm_service.build_report_fallback(conversation_text)

        report = Report(
            consultation_id=consultation.id,
            symptoms_summary=report_payload["symptoms_summary"],
            possible_conditions=json.dumps(report_payload["possible_conditions"], ensure_ascii=False),
            recommended_department=report_payload["recommended_department"],
            urgency_level=report_payload["urgency_level"],
            next_step_advice=report_payload["next_step_advice"],
            disclaimer=report_payload.get("disclaimer", DISCLAIMER_TEXT),
            raw_payload=json.dumps(report_payload, ensure_ascii=False),
        )
        db.session.add(report)
        db.session.commit()
        return report.to_dict()

    def get_latest_report(self, consultation_id):
        consultation = self.consultation_service.get_consultation(consultation_id)
        report = Report.query.filter_by(consultation_id=consultation.id).order_by(Report.created_at.desc()).first()
        if report is None:
            return None
        return report.to_dict()
