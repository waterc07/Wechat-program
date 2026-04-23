import requests

from app.services.llm_service import LLMService


def login_user(client, nickname="stream-user"):
    response = client.post(
        "/api/auth/wx-login",
        json={"code": "test-code", "nickname": nickname},
    )
    return response.get_json()["data"]["user"]["id"]


def test_stream_chat_reply_uses_provider_chunks(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def iter_lines(self, decode_unicode=True):
            yield 'data: {"choices":[{"delta":{"content":"Hello"}}]}'
            yield 'data: {"choices":[{"delta":{"content":" world"}}]}'
            yield "data: [DONE]"

    def fake_post(url, headers, json, timeout, stream):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        captured["stream"] = stream
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

    events = list(
        service.stream_chat_reply(
            [{"role": "user", "content": "hello"}],
            {"latest_user_message": "hello", "locale": "en-US"},
        )
    )

    assert captured["url"] == "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    assert captured["headers"]["Accept"] == "text/event-stream"
    assert captured["json"]["stream"] is True
    assert captured["stream"] is True
    assert [event["content"] for event in events if event["type"] == "delta"] == ["Hello", " world"]
    assert events[-1]["type"] == "complete"
    assert events[-1]["content"] == "Hello world"


def test_stream_chat_reply_falls_back_when_provider_stream_fails(monkeypatch):
    monkeypatch.setattr(
        "app.services.llm_service.requests.post",
        lambda *args, **kwargs: (_ for _ in ()).throw(requests.Timeout("read timeout")),
    )
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

    events = list(
        service.stream_chat_reply(
            [{"role": "user", "content": "I have a fever"}],
            {"latest_user_message": "I have a fever", "locale": "en-US"},
        )
    )

    assert any(event["type"] == "delta" for event in events)
    assert events[-1]["type"] == "complete"
    assert events[-1]["provider"] == "mock"


def test_chat_stream_returns_sse_and_persists_messages(client, monkeypatch):
    user_id = login_user(client, nickname="stream-user")

    def fake_stream_reply(*args, **kwargs):
        yield {"type": "delta", "content": "Hello "}
        yield {"type": "delta", "content": "stream"}
        yield {
            "type": "complete",
            "content": "Hello stream",
            "risk_level": "low",
            "provider": "qwen",
        }

    monkeypatch.setattr("app.routes.chat.LLMService.stream_chat_reply", fake_stream_reply)

    response = client.post(
        "/api/chat/stream",
        json={"user_id": user_id, "message": "start stream"},
        buffered=True,
    )

    body = response.data.decode("utf-8")

    assert response.status_code == 200
    assert response.mimetype == "text/event-stream"
    assert "event: meta" in body
    assert "event: delta" in body
    assert "event: done" in body
    assert "Hello stream" in body

    messages_response = client.get("/api/consultations/1/messages")
    messages_payload = messages_response.get_json()

    assert len(messages_payload["data"]["messages"]) == 2
    assert messages_payload["data"]["messages"][1]["role"] == "assistant"
    assert "Hello stream" in messages_payload["data"]["messages"][1]["content"]
