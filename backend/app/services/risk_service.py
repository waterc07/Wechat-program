import re

from ..constants import EMERGENCY_KEYWORDS


NEGATION_HINTS = [
    "没有",
    "没",
    "无",
    "并无",
    "未",
    "未见",
    "否认",
    "not",
    "no",
    "without",
    "deny",
    "denies",
]

CLAUSE_SPLIT_PATTERN = re.compile(r"(?:[，。；,;\n]|但是|不过|however|but)", re.IGNORECASE)


class RiskService:
    def detect(self, text):
        normalized = (text or "").lower()
        for clause in self._split_clauses(normalized):
            for keyword in EMERGENCY_KEYWORDS["high"]:
                keyword_normalized = keyword.lower()
                if keyword_normalized in clause and not self._is_negated(clause, keyword_normalized):
                    return {
                        "risk_level": "high",
                        "matched_keyword": keyword,
                        "message": "",
                    }
        return {
            "risk_level": "low",
            "matched_keyword": None,
            "message": "",
        }

    def _split_clauses(self, text):
        clauses = [clause.strip() for clause in CLAUSE_SPLIT_PATTERN.split(text) if clause.strip()]
        return clauses or [text]

    def _is_negated(self, clause, keyword):
        for match in re.finditer(re.escape(keyword), clause):
            start = match.start()
            prefix = clause[max(0, start - 12):start].strip()
            if any(prefix.endswith(hint) or f"{hint} " in prefix or hint in prefix for hint in NEGATION_HINTS):
                continue
            return False
        return True
