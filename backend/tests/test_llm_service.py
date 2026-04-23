import requests

from app.constants import get_disclaimer
from app.services.llm_service import LLMService


def test_qwen_chat_uses_compatible_endpoint(monkeypatch):
    captured = {}

    class FakeResponse:
        text = ""

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": "这是来自 Qwen 的预问诊辅助回复。"
                        }
                    }
                ]
            }

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("app.services.llm_service.requests.post", fake_post)

    service = LLMService(
        {
            "LLM_PROVIDER": "qwen",
            "LLM_API_KEY": "test-key",
            "LLM_BASE_URL": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "LLM_MODEL": "qwen3.6-plus",
            "LLM_TIMEOUT_SECONDS": 30,
        }
    )

    result = service.generate_chat_reply(
        [{"role": "user", "content": "我喉咙痛两天"}],
        {"latest_user_message": "我喉咙痛两天"},
    )

    assert captured["url"] == "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"]["model"] == "qwen3.6-plus"
    assert result["provider"] == "qwen"


def test_report_missing_fields_are_filled_with_safe_defaults(monkeypatch):
    class FakeResponse:
        text = ""

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"symptoms_summary":"咳嗽三天","possible_conditions":["上呼吸道感染倾向"]}'
                            )
                        }
                    }
                ]
            }

    monkeypatch.setattr("app.services.llm_service.requests.post", lambda *args, **kwargs: FakeResponse())

    service = LLMService(
        {
            "LLM_PROVIDER": "qwen",
            "LLM_API_KEY": "test-key",
            "LLM_BASE_URL": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "LLM_MODEL": "qwen3.6-plus",
            "LLM_TIMEOUT_SECONDS": 30,
        }
    )

    result = service.generate_report(
        [{"role": "user", "content": "我咳嗽三天"}],
        {"conversation_text": "user: 我咳嗽三天"},
    )

    assert result["symptoms_summary"] == "咳嗽三天"
    assert result["possible_conditions"] == ["上呼吸道感染倾向"]
    assert result["recommended_department"]
    assert result["urgency_level"]
    assert result["next_step_advice"]
    assert result["disclaimer"] == get_disclaimer("zh-CN")


def test_chat_retries_once_after_timeout(monkeypatch):
    call_count = {"value": 0}

    class FakeResponse:
        text = ""

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": "这是重试后成功返回的预问诊回复。"
                        }
                    }
                ]
            }

    def fake_post(*args, **kwargs):
        call_count["value"] += 1
        if call_count["value"] == 1:
            raise requests.Timeout("read timeout")
        return FakeResponse()

    monkeypatch.setattr("app.services.llm_service.requests.post", fake_post)
    monkeypatch.setattr("app.services.llm_service.time.sleep", lambda *_: None)

    service = LLMService(
        {
            "LLM_PROVIDER": "qwen",
            "LLM_API_KEY": "test-key",
            "LLM_BASE_URL": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "LLM_MODEL": "qwen3.6-plus",
            "LLM_TIMEOUT_SECONDS": 30,
        }
    )

    result = service.generate_chat_reply(
        [{"role": "user", "content": "我头痛两天"}],
        {"latest_user_message": "我头痛两天"},
    )

    assert call_count["value"] == 2
    assert result["provider"] == "qwen"
    assert "重试后成功" in result["content"]


def test_chat_markdown_is_normalized_for_miniprogram(monkeypatch):
    class FakeResponse:
        text = ""

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": (
                                "## 预问诊摘要\n"
                                "- **主诉**：发热、咳嗽\n"
                                "- **建议**：补充 `体温` 和症状持续时间\n"
                            )
                        }
                    }
                ]
            }

    monkeypatch.setattr("app.services.llm_service.requests.post", lambda *args, **kwargs: FakeResponse())

    service = LLMService(
        {
            "LLM_PROVIDER": "qwen",
            "LLM_API_KEY": "test-key",
            "LLM_BASE_URL": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "LLM_MODEL": "qwen3.6-plus",
            "LLM_TIMEOUT_SECONDS": 30,
        }
    )

    result = service.generate_chat_reply(
        [{"role": "user", "content": "我发热咳嗽"}],
        {"latest_user_message": "我发热咳嗽"},
    )

    assert "##" not in result["content"]
    assert "**" not in result["content"]
    assert "`" not in result["content"]
    assert "主诉：发热、咳嗽" in result["content"]
    assert "建议：补充体温和症状持续时间" in result["content"]


def test_chat_fallback_avoids_reasking_fever_when_already_mentioned():
    service = LLMService({"LLM_PROVIDER": "mock"})

    result = service.build_chat_fallback("我现在发烧头痛", "zh-CN")

    assert "是否伴有发热" not in result["content"]
    assert "最高体温" in result["content"]


def test_chat_fallback_asks_headache_specific_follow_up():
    service = LLMService({"LLM_PROVIDER": "mock"})

    result = service.build_chat_fallback("我头痛两天", "zh-CN")

    assert "什么部位" in result["content"]
    assert "严重程度" in result["content"]
