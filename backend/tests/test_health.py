def test_health_endpoint(client):
    response = client.get("/api/health")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["data"]["status"] == "ok"

