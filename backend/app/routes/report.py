from flask import Blueprint, current_app, request

from ..schemas.request_validators import get_json_payload, validate_report_payload
from ..schemas.response import success_response
from ..services.report_service import ReportService
from ..utils.errors import NotFoundError
from ..constants import normalize_locale


report_bp = Blueprint("report", __name__, url_prefix="/api/report")


@report_bp.post("/generate")
def generate_report():
    payload = validate_report_payload(get_json_payload())
    report_service = ReportService(current_app.config)
    report = report_service.generate_report(payload["consultation_id"], payload["locale"])
    return success_response(
        {
            "report": report,
        },
        message="Report generated.",
    )


@report_bp.get("/<int:consultation_id>")
def get_report(consultation_id):
    report_service = ReportService(current_app.config)
    locale = request.args.get("locale")
    report = report_service.get_latest_report(
        consultation_id,
        normalize_locale(locale) if locale else None,
    )
    if report is None:
        raise NotFoundError("Report not found.")
    return success_response({"report": report})
