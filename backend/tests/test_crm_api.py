from fastapi.testclient import TestClient

from app.main import app


def test_crm_routes_are_available_and_persist_records():
    with TestClient(app) as client:
        login_response = client.post(
            "/api/auth/login",
            json={"login": "radiologist", "password": "radio123"},
        )
        assert login_response.status_code == 200
        headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

        list_response = client.get("/api/crm", headers=headers)
        assert list_response.status_code == 200
        assert isinstance(list_response.json(), list)

        create_response = client.post(
            "/api/crm",
            headers=headers,
            json={
                "patient_code": "CRM-TEST-001",
                "contact_type": "consultation",
                "status": "active",
                "priority": "normal",
                "summary": "Follow-up call",
                "note": "Patient asked for report clarification.",
                "next_step": "Call patient",
            },
        )
        assert create_response.status_code == 201
        record = create_response.json()
        assert record["patient_code"] == "CRM-TEST-001"
        assert record["created_by"]["login"] == "radiologist"

        patch_response = client.patch(
            f"/api/crm/{record['id']}",
            headers=headers,
            json={"status": "follow_up", "priority": "high"},
        )
        assert patch_response.status_code == 200
        assert patch_response.json()["status"] == "follow_up"
        assert patch_response.json()["priority"] == "high"

        delete_response = client.delete(f"/api/crm/{record['id']}", headers=headers)
        assert delete_response.status_code == 204
