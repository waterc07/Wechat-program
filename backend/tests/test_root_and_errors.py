def test_root_endpoint_returns_service_info(client):
    response = client.get("/")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["data"]["service"] == "medical-pre-diagnosis-assistant"


def test_unknown_route_returns_404_json(client):
    response = client.get("/not-found")
    payload = response.get_json()

    assert response.status_code == 404
    assert payload["success"] is False
    assert payload["code"] == "NOT_FOUND"
