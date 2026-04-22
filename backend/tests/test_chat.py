from app.services.llm_service import LLMServiceError


def login_user(client, nickname="测试用户"):
    response = client.post(
        "/api/auth/wx-login",
        json={"code": "test-code", "nickname": nickname},
    )
    return response.get_json()["data"]["user"]["id"]


def test_chat_creates_consultation_and_messages(client):
    user_id = login_user(client)

    chat_response = client.post(
        "/api/chat",
        json={"user_id": user_id, "message": "我这两天发烧并且咳嗽"},
    )
    payload = chat_response.get_json()

    assert chat_response.status_code == 200
    assert payload["success"] is True
    assert payload["data"]["consultation_id"] > 0
    assert payload["data"]["assistant_message"]["role"] == "assistant"

    messages_response = client.get(
        f"/api/consultations/{payload['data']['consultation_id']}/messages"
    )
    messages_payload = messages_response.get_json()

    assert len(messages_payload["data"]["messages"]) == 2
    assert messages_payload["data"]["messages"][0]["role"] == "user"
    assert messages_payload["data"]["messages"][1]["role"] == "assistant"


def test_chat_emergency_guardrail(client):
    user_id = login_user(client, nickname="紧急用户")

    chat_response = client.post(
        "/api/chat",
        json={"user_id": user_id, "message": "我现在胸痛而且呼吸困难"},
    )
    payload = chat_response.get_json()

    assert chat_response.status_code == 200
    assert payload["data"]["risk_level"] == "high"
    assert "急诊" in payload["data"]["assistant_message"]["content"]


def test_chat_negated_emergency_terms_do_not_trigger_guardrail(client):
    user_id = login_user(client, nickname="否定高风险用户")

    chat_response = client.post(
        "/api/chat",
        json={"user_id": user_id, "message": "已经两天了，最高38.7度，没有胸痛和呼吸困难"},
    )
    payload = chat_response.get_json()

    assert chat_response.status_code == 200
    assert payload["data"]["risk_level"] == "low"
    assert "急诊" not in payload["data"]["assistant_message"]["content"]


def test_chat_fallback_when_llm_fails(client, monkeypatch):
    user_id = login_user(client, nickname="降级用户")

    def raise_error(*args, **kwargs):
        raise LLMServiceError("provider down")

    monkeypatch.setattr("app.routes.chat.LLMService.generate_chat_reply", raise_error)

    chat_response = client.post(
        "/api/chat",
        json={"user_id": user_id, "message": "我头痛，还有一点恶心"},
    )
    payload = chat_response.get_json()

    assert chat_response.status_code == 200
    assert payload["success"] is True
    assert "头痛已经持续多久" in payload["data"]["assistant_message"]["content"]
    assert "疼痛部位和严重程度" in payload["data"]["assistant_message"]["content"]
