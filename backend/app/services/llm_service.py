import json
import re
import time

import requests

from ..constants import (
    get_default_assistant_question,
    get_disclaimer,
    normalize_locale,
)
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
            content = self._normalize_chat_text(content)
            return {
                "content": content,
                "risk_level": "low",
                "provider": self.provider,
            }
        except LLMServiceError:
            raise
        except Exception as error:  # noqa: BLE001
            raise LLMServiceError(data={"detail": str(error)}) from error

    def stream_chat_reply(self, messages, fallback_context):
        if not self._use_external_provider():
            yield from self._stream_fallback_chat_reply(fallback_context)
            return

        accumulated = []

        try:
            for payload in self._stream_chat_completion(messages=messages, temperature=0.2):
                delta = self._extract_stream_message_delta(payload)
                if not delta:
                    continue
                accumulated.append(delta)
                yield {"type": "delta", "content": delta}

            content = self._normalize_chat_text("".join(accumulated))
            if not content:
                raise LLMServiceError("Provider returned empty chat content.")

            yield {
                "type": "complete",
                "content": content,
                "risk_level": "low",
                "provider": self.provider,
            }
        except LLMServiceError as error:
            if accumulated:
                logger.warning(
                    "Streaming provider interrupted after partial response; returning collected content. detail=%s",
                    error.data or {"detail": str(error)},
                )
                yield {
                    "type": "complete",
                    "content": self._normalize_chat_text("".join(accumulated)),
                    "risk_level": "low",
                    "provider": self.provider,
                }
                return

            logger.warning(
                "Streaming provider call failed, using fallback. detail=%s",
                error.data or {"detail": str(error)},
            )
            yield from self._stream_fallback_chat_reply(fallback_context)
        except Exception as error:  # noqa: BLE001
            logger.warning(
                "Unexpected streaming provider error, using fallback. detail=%s",
                {"detail": str(error)},
            )
            yield from self._stream_fallback_chat_reply(fallback_context)

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

    def build_chat_fallback(self, latest_user_message, locale="zh-CN", conversation_text=""):
        return self._mock_chat_reply(
            {
                "latest_user_message": latest_user_message,
                "locale": locale,
                "conversation_text": conversation_text,
            }
        )

    def build_report_fallback(self, conversation_text, locale="zh-CN"):
        return self._mock_report({"conversation_text": conversation_text, "locale": locale})

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

    def _stream_chat_completion(self, *, messages, temperature):
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
            "stream_options": {"include_usage": True},
        }

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                response = requests.post(
                    self._chat_completions_url(),
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "Accept": "text/event-stream",
                    },
                    json=payload,
                    timeout=self.timeout_seconds,
                    stream=True,
                )
                response.raise_for_status()
                break
            except requests.Timeout as error:
                last_error = error
                logger.warning(
                    "Streaming LLM request timed out on attempt %s/%s for provider=%s model=%s",
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
            raise LLMServiceError(
                data={"detail": str(last_error) if last_error else "Unknown request failure."}
            )

        try:
            for raw_line in response.iter_lines(decode_unicode=True):
                if raw_line is None:
                    continue

                line = raw_line.strip()
                if not line or not line.startswith("data:"):
                    continue

                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    break

                try:
                    yield json.loads(data_str)
                except json.JSONDecodeError as error:
                    raise LLMServiceError(
                        "Provider returned invalid streaming payload.",
                        data={"detail": str(error), "body": data_str[:500]},
                    ) from error
        except requests.RequestException as error:
            raise LLMServiceError(data={"detail": str(error)}) from error

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

    def _extract_stream_message_delta(self, data):
        try:
            delta = data["choices"][0]["delta"]
        except (KeyError, IndexError, TypeError):
            return ""

        content = delta.get("content", "")
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(item.get("text", ""))
                elif isinstance(item, str):
                    parts.append(item)
            return "".join(parts)

        if isinstance(content, str):
            return content
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

    def _normalize_chat_text(self, content):
        normalized = content.replace("\r\n", "\n").strip()
        normalized = re.sub(r"```(?:[\w+-]+)?\s*", "", normalized)
        normalized = normalized.replace("```", "")
        normalized = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", normalized)
        normalized = re.sub(r"(\*\*|__)(.*?)\1", r"\2", normalized)
        normalized = re.sub(r"(?<!\*)\*(?!\*)(.*?)\*(?<!\*)", r"\1", normalized)
        normalized = re.sub(r"(?<!_)_(?!_)(.*?)_(?<!_)", r"\1", normalized)
        normalized = re.sub(r"`([^`]+)`", r"\1", normalized)
        normalized = re.sub(r"(?m)^\s*[-*•]\s+", "• ", normalized)
        normalized = re.sub(r"(?m)^\s*\d+\.\s+", lambda match: match.group(0).strip() + " ", normalized)
        normalized = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", normalized)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        return normalized.strip()

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
                normalized[field] = safe_defaults["disclaimer"]
                if value != safe_defaults["disclaimer"]:
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

    def _stream_fallback_chat_reply(self, fallback_context):
        fallback = self._mock_chat_reply(fallback_context)
        for chunk in self._chunk_text_for_stream(fallback["content"]):
            yield {"type": "delta", "content": chunk}
        yield {"type": "complete", **fallback}

    def _chunk_text_for_stream(self, text):
        if not text:
            return []

        chunk_size = 24 if " " in text else 12
        return [text[index : index + chunk_size] for index in range(0, len(text), chunk_size)]

    def _mock_chat_reply(self, fallback_context):
        latest_user_message = fallback_context.get("latest_user_message", "")
        locale = normalize_locale(fallback_context.get("locale"))
        follow_up_question = self._build_contextual_follow_up(latest_user_message, locale)

        if locale == "en-US":
            summary = latest_user_message[:120] or "You have provided an initial symptom description"
            content = (
                f"I've received your symptom description: {summary}. "
                "The current information is only for pre-visit organization and does not replace a doctor's diagnosis. "
                f"{follow_up_question}"
            )
        else:
            summary = latest_user_message[:120] or "您已提供初步症状描述"
            content = (
                f"已收到您的症状描述：{summary}。当前信息仅用于就诊前整理，不能替代医生诊断。"
                f"{follow_up_question}"
            )
        return {"content": content, "risk_level": "low", "provider": "mock"}

    def _build_contextual_follow_up(self, latest_user_message, locale):
        text = (latest_user_message or "").lower()

        if locale == "en-US":
            if any(word in text for word in ["fever", "temperature"]):
                return (
                    "Please add how many days this has lasted, the highest temperature, and whether you also have cough, sore throat, chills, or worsening symptoms."
                )
            if any(word in text for word in ["headache", "head pain"]):
                return (
                    "Please add how long the headache has lasted, where it is located, how severe it is, and whether it is accompanied by fever, nausea, or dizziness."
                )
            if any(word in text for word in ["cough", "sore throat", "throat pain"]):
                return (
                    "Please add how long this has lasted, whether you have sputum or fever, and whether swallowing or coughing makes it worse."
                )
            return get_default_assistant_question(locale)

        if any(word in text for word in ["发烧", "发热", "低烧", "高烧", "体温"]):
            return "请补充已经持续了几天、最高体温大概多少，以及是否伴有咳嗽、咽痛、怕冷或症状加重。"
        if any(word in text for word in ["头痛", "头疼", "头部疼痛"]):
            return "请补充头痛已经持续多久、疼痛部位和严重程度，以及是否伴有发热、恶心、眩晕或畏光。"
        if any(word in text for word in ["咳嗽", "喉咙痛", "咽痛", "嗓子痛"]):
            return "请补充症状已经持续多久，是否有痰或发热，以及吞咽或咳嗽时是否明显加重。"
        return get_default_assistant_question(locale)

    def _mock_chat_reply(self, fallback_context):
        latest_user_message = fallback_context.get("latest_user_message", "")
        locale = normalize_locale(fallback_context.get("locale"))
        conversation_text = fallback_context.get("conversation_text", "")
        context_text = f"{conversation_text}\n{latest_user_message}".strip()
        summary = self._summarize_user_message(latest_user_message, locale)
        acknowledgement = self._build_acknowledgement(latest_user_message, locale)
        follow_up_question = self._build_contextual_follow_up(
            latest_user_message,
            locale,
            context_text=context_text,
        )

        if locale == "en-US":
            content = (
                f"{acknowledgement} "
                f"So far I understand the main issue as: {summary}. "
                f"{follow_up_question}"
            )
        else:
            content = (
                f"{acknowledgement}"
                f"我先理解为：{summary}。"
                f"{follow_up_question}"
            )
        return {"content": content, "risk_level": "low", "provider": "mock"}

    def _build_acknowledgement(self, latest_user_message, locale):
        text = (latest_user_message or "").lower()

        if locale == "en-US":
            if any(word in text for word in ["pain", "hurt", "ache"]):
                return "I understand that this has been uncomfortable."
            if any(word in text for word in ["fever", "temperature", "cough", "vomit", "nausea"]):
                return "Thanks, that gives me a clearer picture of what you're experiencing."
            return "I understand what you've described."

        if any(word in text for word in ["痛", "疼", "难受"]):
            return "明白，这样确实会让人不舒服。"
        if any(word in text for word in ["发烧", "发热", "咳嗽", "恶心", "呕吐"]):
            return "收到，这样我对您目前的情况更清楚一些。"
        return "收到，我已经理解您刚才描述的情况。"

    def _summarize_user_message(self, latest_user_message, locale):
        cleaned = re.sub(r"\s+", " ", (latest_user_message or "")).strip()
        if cleaned:
            return cleaned[:120]

        if locale == "en-US":
            return "you have described an initial symptom concern"
        return "您提供了初步的症状描述"

    def _build_contextual_follow_up(self, latest_user_message, locale, context_text=""):
        text = (latest_user_message or "").lower()
        full_text = (context_text or latest_user_message or "").lower()

        if locale == "en-US":
            if any(word in full_text for word in ["fever", "temperature"]):
                missing = self._build_missing_fever_fields_en(full_text)
                if missing:
                    return f"To narrow it down, please add {', '.join(missing)}."
                return "Next, please note whether the cough has sputum, whether symptoms are getting worse, and whether medicine or rest helps."
            if any(word in full_text for word in ["headache", "head pain"]):
                missing = self._build_missing_headache_fields_en(full_text)
                if missing:
                    return f"What I still need most is {', '.join(missing)}."
                return "Next, please watch whether the headache worsens, becomes one-sided, or comes with vomiting, stiff neck, or unusual drowsiness."
            if any(word in text for word in ["cough", "sore throat", "throat pain"]):
                return (
                    "What I want to confirm next is how long this has lasted, whether you have sputum or fever, and whether swallowing or coughing makes it worse?"
                )
            return get_default_assistant_question(locale)

        if any(word in full_text for word in ["发烧", "发热", "低烧", "高烧", "体温"]):
            missing = self._build_missing_fever_fields_zh(full_text)
            if missing:
                return f"我现在还需要补充确认：{'、'.join(missing)}。"
            return "接下来更需要确认的是：咳嗽有没有痰，症状是在加重还是缓解，用过退烧药后体温能不能降下来。"
        if any(word in full_text for word in ["头痛", "头疼", "头部疼痛"]):
            missing = self._build_missing_headache_fields_zh(full_text)
            if missing:
                return f"我现在还需要补充确认：{'、'.join(missing)}。"
            return "接下来请留意头痛是否加重，是否出现喷射性呕吐、颈部僵硬、明显嗜睡或意识异常。"
        if any(word in text for word in ["咳嗽", "喉咙痛", "咽痛", "嗓子痛"]):
            return "接下来我想确认一下：症状持续多久了，有没有痰或发热，吞咽时会不会更明显？"
        return get_default_assistant_question(locale)

    def _build_missing_fever_fields_zh(self, text):
        fields = []
        if not self._mentions_duration_zh(text):
            fields.append("症状已经持续几天")
        if not self._mentions_temperature(text):
            fields.append("最高体温大概多少")
        if "咳嗽" not in text:
            fields.append("是否伴有咳嗽")
        if not any(word in text for word in ["咽痛", "喉咙痛", "嗓子痛"]):
            fields.append("是否咽痛")
        if not any(word in text for word in ["怕冷", "畏寒", "寒战"]):
            fields.append("是否怕冷或寒战")
        return fields[:3]

    def _build_missing_headache_fields_zh(self, text):
        fields = []
        if not self._mentions_duration_zh(text):
            fields.append("头痛持续了多久")
        if not any(word in text for word in ["前额", "太阳穴", "后脑", "头顶", "一侧", "两侧", "部位"]):
            fields.append("主要在什么部位")
        if not any(word in text for word in ["轻", "中", "重", "严重", "剧烈", "程度"]):
            fields.append("疼痛严重程度")
        if "恶心" not in text and "呕吐" not in text:
            fields.append("是否恶心或呕吐")
        return fields[:3]

    def _mentions_duration_zh(self, text):
        return bool(
            re.search(r"(持续|已经|有|第|今天第).{0,8}(天|日|周|星期|小时)", text)
            or re.search(r"\d+\s*(天|日|周|星期|小时)", text)
            or re.search(r"[一二两三四五六七八九十]+天", text)
        )

    def _mentions_temperature(self, text):
        return bool(re.search(r"\d{2}(?:\.\d)?\s*(?:度|℃|°c?)", text) or "最高体温" in text)

    def _build_missing_fever_fields_en(self, text):
        fields = []
        if not re.search(r"\b\d+\s*(day|days|hour|hours|week|weeks)\b", text):
            fields.append("how long it has lasted")
        if not re.search(r"\b\d{2,3}(?:\.\d)?\s*(?:c|f|°|degrees?)?\b", text):
            fields.append("the highest temperature")
        if "cough" not in text:
            fields.append("whether there is cough")
        if "sore throat" not in text and "throat pain" not in text:
            fields.append("whether there is sore throat")
        return fields[:3]

    def _build_missing_headache_fields_en(self, text):
        fields = []
        if not re.search(r"\b\d+\s*(day|days|hour|hours|week|weeks)\b", text):
            fields.append("how long the headache has lasted")
        if not any(word in text for word in ["forehead", "temple", "back of head", "one side", "both sides", "location"]):
            fields.append("where it is located")
        if not any(word in text for word in ["mild", "moderate", "severe", "intense", "severity"]):
            fields.append("how severe it is")
        return fields[:3]

    def _mock_report(self, fallback_context):
        conversation_text = fallback_context.get("conversation_text", "")
        locale = normalize_locale(fallback_context.get("locale"))
        lower_text = conversation_text.lower()
        urgency_level = (
            "medium"
            if any(word in lower_text for word in ["pain", "疼", "痛", "发烧", "fever"])
            else "low"
        )
        if locale == "en-US":
            possible_conditions = (
                ["Upper respiratory infection", "Digestive discomfort"]
                if any(
                    word in lower_text
                    for word in ["发烧", "fever", "咳", "cough", "恶心", "nausea"]
                )
                else ["Needs further evaluation", "Common mild discomfort"]
            )
            symptoms_summary = conversation_text[:300] or "The patient has provided an initial symptom description."
            recommended_department = "General medicine"
            next_step_advice = (
                "Please add the symptom onset time, duration, triggers, and associated symptoms, and visit an in-person clinic "
                "for further evaluation by a doctor as soon as possible."
            )
        else:
            possible_conditions = (
                ["上呼吸道感染", "消化系统不适"]
                if any(
                    word in lower_text
                    for word in ["发烧", "fever", "咳", "cough", "恶心", "nausea"]
                )
                else ["待进一步检查明确", "常见轻症不适"]
            )
            symptoms_summary = conversation_text[:300] or "患者已提供初步症状描述。"
            recommended_department = "全科门诊"
            next_step_advice = (
                "建议补充症状起始时间、持续时长、诱因和伴随症状，并尽快前往线下门诊由医生进一步评估。"
            )
        return {
            "symptoms_summary": symptoms_summary,
            "possible_conditions": possible_conditions,
            "recommended_department": recommended_department,
            "urgency_level": urgency_level,
            "next_step_advice": next_step_advice,
            "disclaimer": get_disclaimer(locale),
        }
