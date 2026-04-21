def login_user(client, nickname="报告用户"):
    response = client.post(
        "/api/auth/wx-login",
        json={"code": f"{nickname}-code", "nickname": nickname},
    )
    return response.get_json()["data"]["user"]["id"]


def test_generate_and_fetch_report(client):
    user_id = login_user(client)
    chat_response = client.post(
        "/api/chat",
        json={"user_id": user_id, "message": "我发烧两天，伴随喉咙痛"},
    )
    consultation_id = chat_response.get_json()["data"]["consultation_id"]

    generate_response = client.post(
        "/api/report/generate",
        json={"consultation_id": consultation_id},
    )
    generate_payload = generate_response.get_json()

    assert generate_response.status_code == 200
    assert generate_payload["data"]["report"]["consultation_id"] == consultation_id
    assert generate_payload["data"]["report"]["symptoms_summary"]
    assert generate_payload["data"]["report"]["disclaimer"]

    fetch_response = client.get(f"/api/report/{consultation_id}")
    fetch_payload = fetch_response.get_json()

    assert fetch_response.status_code == 200
    assert fetch_payload["data"]["report"]["consultation_id"] == consultation_id
    assert isinstance(fetch_payload["data"]["report"]["possible_conditions"], list)


def test_generate_report_falls_back_on_invalid_provider_json(client, monkeypatch):
    user_id = login_user(client, nickname="JSON降级用户")
    chat_response = client.post(
        "/api/chat",
        json={"user_id": user_id, "message": "我最近咳嗽三天，晚上更明显"},
    )
    consultation_id = chat_response.get_json()["data"]["consultation_id"]

    monkeypatch.setitem(client.application.config, "LLM_PROVIDER", "qwen")
    monkeypatch.setitem(client.application.config, "LLM_API_KEY", "fake-key")

    class FakeResponse:
        text = "not json"

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": "not-json-response"
                        }
                    }
                ]
            }

    monkeypatch.setattr("app.services.llm_service.requests.post", lambda *args, **kwargs: FakeResponse())

    generate_response = client.post(
        "/api/report/generate",
        json={"consultation_id": consultation_id},
    )
    payload = generate_response.get_json()

    assert generate_response.status_code == 200
    assert payload["success"] is True
    assert payload["data"]["report"]["disclaimer"]
    assert isinstance(payload["data"]["report"]["possible_conditions"], list)
