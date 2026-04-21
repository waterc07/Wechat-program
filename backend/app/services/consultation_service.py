from ..extensions import db
from ..models import Consultation, Message, User
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

    def add_message(self, consultation, role, content, risk_level="low"):
        message = Message(
            consultation_id=consultation.id,
            role=role,
            content=content,
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
