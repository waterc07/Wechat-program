from app.routes.chat import _create_fast_chat_llm_service


def test_fast_chat_llm_service_caps_timeout_and_disables_retries(app):
    app.config.update(
        {
            "LLM_PROVIDER": "qwen",
            "LLM_API_KEY": "test-key",
            "LLM_TIMEOUT_SECONDS": 30,
            "CHAT_LLM_TIMEOUT_SECONDS": 8,
        }
    )

    with app.app_context():
        service = _create_fast_chat_llm_service()

    assert service.timeout_seconds == 8
    assert service.max_retries == 0
