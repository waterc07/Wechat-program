from app.constants import get_disclaimer
from app.services.llm_service import LLMService
from app.services.prompt_builder import build_chat_messages, build_report_messages


def test_prompt_builder_uses_english_system_prompts():
    chat_messages = build_chat_messages([], "I have a fever and cough", "en-US")
    report_messages = build_report_messages(
        [{"role": "user", "content": "I have a fever and cough"}],
        "en-US",
    )

    assert "Reply in English" in chat_messages[0]["content"]
    assert "Please output in English" in report_messages[0]["content"]
    assert get_disclaimer("en-US") in report_messages[-1]["content"]


def test_mock_fallback_uses_english_locale():
    service = LLMService({"LLM_PROVIDER": "mock"})

    chat_result = service.build_chat_fallback("I have had a fever for two days", "en-US")
    report_result = service.build_report_fallback(
        "user: I have had a fever for two days",
        "en-US",
    )

    assert "So far I understand the main issue as:" in chat_result["content"]
    assert "highest temperature" in chat_result["content"]
    assert report_result["recommended_department"] == "General medicine"
    assert report_result["disclaimer"] == get_disclaimer("en-US")


def test_chat_endpoint_returns_english_disclaimer(client):
    login_response = client.post(
        "/api/auth/wx-login",
        json={"code": "english-user", "nickname": "English User"},
    )
    user_id = login_response.get_json()["data"]["user"]["id"]

    chat_response = client.post(
        "/api/chat",
        json={
            "user_id": user_id,
            "message": "I have a fever and a sore throat",
            "locale": "en-US",
        },
    )
    payload = chat_response.get_json()

    assert chat_response.status_code == 200
    assert payload["data"]["disclaimer"] == get_disclaimer("en-US")
    assert get_disclaimer("en-US") not in payload["data"]["assistant_message"]["content"]
