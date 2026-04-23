from unittest.mock import patch


def login_user(client, nickname="history-user"):
    response = client.post(
        "/api/auth/wx-login",
        json={"code": "test-code", "nickname": nickname},
    )
    return response.get_json()["data"]["user"]["id"]


def test_list_consultations_returns_recent_first(client):
    user_id = login_user(client)

    with patch("app.services.llm_service.time.sleep", lambda *_: None):
        first_response = client.post(
            "/api/chat",
            json={"user_id": user_id, "message": "First symptom message"},
        )
        second_response = client.post(
            "/api/chat",
            json={"user_id": user_id, "message": "Second symptom message"},
        )

    first_consultation_id = first_response.get_json()["data"]["consultation_id"]
    second_consultation_id = second_response.get_json()["data"]["consultation_id"]

    response = client.get(f"/api/consultations?user_id={user_id}")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert [item["id"] for item in payload["data"]["consultations"]] == [
        second_consultation_id,
        first_consultation_id,
    ]
    assert payload["data"]["consultations"][0]["message_count"] == 2
    assert payload["data"]["consultations"][0]["last_message_preview"]


def test_list_consultations_requires_user_id(client):
    response = client.get("/api/consultations")
    payload = response.get_json()

    assert response.status_code == 400
    assert payload["success"] is False
    assert payload["code"] == "VALIDATION_ERROR"
