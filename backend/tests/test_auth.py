def test_wx_login_prefers_cloud_container_openid(client):
    response = client.post(
        "/api/auth/wx-login",
        json={"code": "dev-code", "nickname": "Cloud User"},
        headers={
            "X-WX-OPENID": "cloud-openid-001",
            "X-WX-APPID": "wx-test-appid",
            "X-WX-UNIONID": "union-001",
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    data = payload["data"]
    assert data["is_mock_login"] is False
    assert data["wechat_appid"] == "wx-test-appid"
    assert data["wechat_unionid"] == "union-001"
    assert data["user"]["wx_openid"] == "cloud-openid-001"
    assert data["user"]["nickname"] == "Cloud User"


def test_wx_login_falls_back_to_mock_openid_for_local_http(client):
    response = client.post(
        "/api/auth/wx-login",
        json={"code": "", "mock_openid": "local-openid-001", "nickname": "Local User"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    data = payload["data"]
    assert data["is_mock_login"] is True
    assert data["wechat_appid"] is None
    assert data["user"]["wx_openid"] == "local-openid-001"


def test_wx_login_rejects_missing_cloud_openid_in_production(client):
    client.application.config["FLASK_ENV"] = "production"

    response = client.post(
        "/api/auth/wx-login",
        json={"code": "dev-code", "nickname": "Production User"},
    )

    assert response.status_code == 401
    payload = response.get_json()
    assert payload["success"] is False
    assert payload["code"] == "WECHAT_OPENID_REQUIRED"
