from ..constants import EMERGENCY_ESCALATION_MESSAGE, EMERGENCY_KEYWORDS


class RiskService:
    def detect(self, text):
        normalized = (text or "").lower()
        for keyword in EMERGENCY_KEYWORDS["high"]:
            if keyword.lower() in normalized:
                return {
                    "risk_level": "high",
                    "matched_keyword": keyword,
                    "message": EMERGENCY_ESCALATION_MESSAGE,
                }
        return {
            "risk_level": "low",
            "matched_keyword": None,
            "message": "",
        }

