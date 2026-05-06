from sqlalchemy import func

from ..extensions import db
from ..models import Consultation, Message, Report, User
from ..utils.errors import NotFoundError


class ConsultationService:
    def get_user(self, user_id):
        user = db.session.get(User, user_id)
        if user is None:
            raise NotFoundError("User not found.")
        return user

    def get_consultation(self, consultation_id):
        consultation = db.session.get(Consultation, consultation_id)
        if consultation is None:
            raise NotFoundError("Consultation not found.")
        return consultation

    def get_or_create_consultation(self, user_id, consultation_id=None, chief_complaint=""):
        self.get_user(user_id)

        if consultation_id is not None:
            consultation = self.get_consultation(consultation_id)
            if consultation.user_id != user_id:
                raise NotFoundError("Consultation not found for the user.")
            return consultation, False

        consultation = Consultation(
            user_id=user_id,
            chief_complaint=chief_complaint[:512],
            risk_level="low",
        )
        db.session.add(consultation)
        db.session.commit()
        return consultation, True

    def find_message_by_client_request_id(self, consultation_id, client_request_id):
        if not client_request_id:
            return None
        return Message.query.filter_by(
            consultation_id=consultation_id,
            client_request_id=client_request_id,
        ).first()

    def add_message(self, consultation, role, content, risk_level="low", client_request_id=""):
        message = Message(
            consultation_id=consultation.id,
            role=role,
            content=content,
            client_request_id=client_request_id or None,
            risk_level=risk_level,
        )
        db.session.add(message)

        if role == "user" and not consultation.chief_complaint:
            consultation.chief_complaint = content[:512]
        consultation.risk_level = risk_level if risk_level == "high" else consultation.risk_level

        db.session.commit()
        return message

    def list_messages(self, consultation_id):
        consultation = self.get_consultation(consultation_id)
        return [message.to_dict() for message in consultation.messages], consultation

    def list_consultations(self, user_id):
        self.get_user(user_id)

        consultations = (
            Consultation.query.filter_by(user_id=user_id)
            .order_by(Consultation.created_at.desc())
            .all()
        )
        if not consultations:
            return []

        consultation_ids = [consultation.id for consultation in consultations]
        message_counts = self._count_by_consultation(Message, consultation_ids)
        report_counts = self._count_by_consultation(Report, consultation_ids)
        latest_messages = self._latest_messages_by_consultation(consultation_ids)

        items = []
        for consultation in consultations:
            last_message = latest_messages.get(consultation.id)
            last_message_at = (
                last_message.created_at.isoformat()
                if last_message is not None
                else consultation.updated_at.isoformat()
            )
            last_message_preview = (
                last_message.content.strip().replace("\n", " ")[:120]
                if last_message is not None
                else consultation.chief_complaint
            )
            items.append(
                {
                    **consultation.to_dict(),
                    "message_count": message_counts.get(consultation.id, 0),
                    "report_count": report_counts.get(consultation.id, 0),
                    "last_message_at": last_message_at,
                    "last_message_preview": last_message_preview,
                    "latest_message_role": last_message.role if last_message is not None else "",
                }
            )

        items.sort(key=lambda item: item["last_message_at"], reverse=True)
        return items

    def _count_by_consultation(self, model, consultation_ids):
        return {
            consultation_id: count
            for consultation_id, count in db.session.query(
                model.consultation_id,
                func.count(model.id),
            )
            .filter(model.consultation_id.in_(consultation_ids))
            .group_by(model.consultation_id)
            .all()
        }

    def _latest_messages_by_consultation(self, consultation_ids):
        latest_message_ids = (
            db.session.query(
                Message.consultation_id,
                func.max(Message.id).label("message_id"),
            )
            .filter(Message.consultation_id.in_(consultation_ids))
            .group_by(Message.consultation_id)
            .subquery()
        )

        messages = (
            Message.query.join(
                latest_message_ids,
                Message.id == latest_message_ids.c.message_id,
            )
            .all()
        )
        return {message.consultation_id: message for message in messages}
