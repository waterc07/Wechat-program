import json
import re
import time

import requests

from ..constants import DEFAULT_ASSISTANT_QUESTION, DISCLAIMER_TEXT
from ..utils.errors import ServiceError
from ..utils.logging import get_logger


logger = get_logger(__name__)

DEFAULT_QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_QWEN_MODEL = "qwen3.6-plus"
REPORT_REQUIRED_FIELDS = (
    "symptoms_summary",
    "possible_conditions",
    "recommended_department",
    "urgency_level",
    "next_step_advice",
    "disclaimer",
)


class LLMServiceError(ServiceError):
    def __init__(self, message="LLM provider call failed.", data=None):
        super().__init__(
            message,
            status_code=502,
            error_code="LLM_PROVIDER_ERROR",
            data=data,
        )


class LLMService:
    def __init__(self, config):
        self.provider = (config.get("LLM_PROVIDER", "mock") or "mock").lower()
        self.base_url = (
            config.get("LLM_BASE_URL")
            or config.get("LLM_API_URL")
            or DEFAULT_QWEN_BASE_URL
        ).rstrip("/")
        self.api_key = config.get("LLM_API_KEY", "")
        self.model = config.get("LLM_MODEL") or DEFAULT_QWEN_MODEL
        self.timeout_seconds = int(config.get("LLM_TIMEOUT_SECONDS", 30))
        self.max_retries = 1

    def generate_chat_reply(self, messages, fallback_context):
        if not self._use_external_provider():
            return self._mock_chat_reply(fallback_context)

        try:
            data = self._post_chat_completion(messages=messages, temperature=0.2)
            content = self._extract_message_content(data)
            if not content:
                raise LLMServiceError(
                    "Provider returned empty chat content.",
                    data={"response": data},
                )
            return {
                "content": content,
                "risk_level": "low",
                "provider": self.provider,
            }
        except LLMServiceError:
            raise
        except Exception as error:  # noqa: BLE001
            raise LLMServiceError(data={"detail": str(error)}) from error

    def generate_report(self, messages, fallback_context):
        if not self._use_external_provider():
            return self._mock_report(fallback_context)

        try:
            data = self._post_chat_completion(
                messages=messages,
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            content = self._extract_message_content(data)
            if not content:
                logger.warning("Provider returned empty report content; using safe fallback.")
                return self._mock_report(fallback_context)

            report_payload = self._safe_parse_json_object(content)
            if report_payload is None:
                logger.warning("Provider report content was not valid JSON; using safe fallback.")
                return self._mock_report(fallback_context)

            return self._normalize_report_payload(report_payload, fallback_context)
        except LLMServiceError:
            raise
        except Exception as error:  # noqa: BLE001
            raise LLMServiceError(data={"detail": str(error)}) from error

    def build_chat_fallback(self, latest_user_message):
        return self._mock_chat_reply({"latest_user_message": latest_user_message})

    def build_report_fallback(self, conversation_text):
        return self._mock_report({"conversation_text": conversation_text})

    def _use_external_provider(self):
        if self.provider == "mock":
            return False
        if self.provider == "qwen":
            return bool(self.api_key)
        return bool(self.api_key and self.base_url and self.model)

    def _post_chat_completion(self, *, messages, temperature, response_format=None):
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format:
            payload["response_format"] = response_format

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                response = requests.post(
                    self._chat_completions_url(),
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=self.timeout_seconds,
                )
                response.raise_for_status()
                break
            except requests.Timeout as error:
                last_error = error
                logger.warning(
                    "LLM request timed out on attempt %s/%s for provider=%s model=%s",
                    attempt + 1,
                    self.max_retries + 1,
                    self.provider,
                    self.model,
                )
                if attempt >= self.max_retries:
                    raise LLMServiceError(data={"detail": str(error)}) from error
                time.sleep(1)
            except requests.RequestException as error:
                raise LLMServiceError(data={"detail": str(error)}) from error
        else:
            raise LLMServiceError(data={"detail": str(last_error) if last_error else "Unknown request failure."})

        try:
            return response.json()
        except ValueError as error:
            raise LLMServiceError(
                "Provider returned non-JSON response.",
                data={"detail": str(error), "body": response.text[:500]},
            ) from error

    def _chat_completions_url(self):
        return f"{self.base_url}/chat/completions"

    def _extract_message_content(self, data):
        try:
            message = data["choices"][0]["message"]
            content = message.get("content", "")
        except (KeyError, IndexError, TypeError) as error:
            raise LLMServiceError(
                "Provider response missing choices/message content.",
                data={"detail": str(error), "response": data},
            ) from error

        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(item.get("text", ""))
                elif isinstance(item, str):
                    parts.append(item)
            return "".join(parts).strip()

        if isinstance(content, str):
            return content.strip()
        return ""

    def _safe_parse_json_object(self, content):
        cleaned = content.strip()
        code_block_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", cleaned, re.DOTALL)
        if code_block_match:
            cleaned = code_block_match.group(1).strip()

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            return None

        if not isinstance(parsed, dict):
            return None
        return parsed

    def _normalize_report_payload(self, payload, fallback_context):
        safe_defaults = self._mock_report(fallback_context)
        normalized = {}

        for field in REPORT_REQUIRED_FIELDS:
            value = payload.get(field)

            if field == "possible_conditions":
                normalized[field] = self._normalize_possible_conditions(
                    value,
                    safe_defaults[field],
                )
                if normalized[field] == safe_defaults[field] and value != normalized[field]:
                    logger.warning(
                        "Provider report missing or invalid field '%s'; using safe default.",
                        field,
                    )
                continue

            if field == "disclaimer":
                normalized[field] = DISCLAIMER_TEXT
                if value != DISCLAIMER_TEXT:
                    logger.warning(
                        "Provider report disclaimer replaced with local safety disclaimer."
                    )
                continue

            if isinstance(value, str) and value.strip():
                normalized[field] = value.strip()
            else:
                normalized[field] = safe_defaults[field]
                logger.warning(
                    "Provider report missing or invalid field '%s'; using safe default.",
                    field,
                )

        return normalized

    def _normalize_possible_conditions(self, value, default):
        if isinstance(value, list):
            cleaned = [str(item).strip() for item in value if str(item).strip()]
            if cleaned:
                return cleaned
            return default

        if isinstance(value, str) and value.strip():
            return [value.strip()]

        return default

    def _mock_chat_reply(self, fallback_context):
        latest_user_message = fallback_context.get("latest_user_message", "")
        summary = latest_user_message[:120] or "您已提供初步症状描述"
        content = (
            f"已收到您的症状描述：{summary}。当前信息仅用于就诊前整理，不能替代医生诊断。"
            f"{DEFAULT_ASSISTANT_QUESTION}"
        )
        return {"content": content, "risk_level": "low", "provider": "mock"}

    def _mock_report(self, fallback_context):
        conversation_text = fallback_context.get("conversation_text", "")
        lower_text = conversation_text.lower()
        urgency_level = (
            "medium"
            if any(word in lower_text for word in ["pain", "疼", "痛", "发烧", "fever"])
            else "low"
        )
        possible_conditions = (
            ["上呼吸道感染", "消化系统不适"]
            if any(
                word in lower_text
                for word in ["发烧", "fever", "咳", "cough", "恶心", "nausea"]
            )
            else ["待进一步检查明确", "常见轻症不适"]
        )
        return {
            "symptoms_summary": conversation_text[:300] or "患者已提供初步症状描述。",
            "possible_conditions": possible_conditions,
            "recommended_department": "全科门诊",
            "urgency_level": urgency_level,
            "next_step_advice": (
                "建议补充症状起始时间、持续时长、诱因和伴随症状，并尽快前往线下门诊由医生进一步评估。"
            ),
            "disclaimer": DISCLAIMER_TEXT,
        }
