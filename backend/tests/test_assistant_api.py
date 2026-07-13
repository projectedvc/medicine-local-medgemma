from fastapi.testclient import TestClient

from app.main import app


def test_assistant_requires_backend_key_without_exposing_provider_details():
    with TestClient(app) as client:
        login_response = client.post(
            "/api/auth/login",
            json={"login": "radiologist", "password": "radio123"},
        )
        headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}
        response = client.post(
            "/api/assistant/chat",
            headers=headers,
            json={"lang": "ru", "messages": [{"role": "user", "content": "Помоги оформить заметку"}]},
        )
        assert response.status_code == 503
        assert "GROQ_API_KEY" in response.json()["detail"]
