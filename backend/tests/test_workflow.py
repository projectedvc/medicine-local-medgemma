import os
from pathlib import Path

from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from app.main import app  # noqa: E402


def test_upload_ai_report_export_workflow(tmp_path):
    image_path = tmp_path / "chest.png"
    Image.new("L", (96, 96), color=92).save(image_path)

    with TestClient(app) as client:
        login_response = client.post(
            "/api/auth/login",
            json={"login": "radiologist", "password": "radio123"},
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        study_response = client.post(
            "/api/studies",
            headers=headers,
            json={"patient_code": "TEST-001", "study_type": "ОГК", "clinical_note": "pytest workflow"},
        )
        assert study_response.status_code == 201
        study_id = study_response.json()["id"]

        with image_path.open("rb") as handle:
            upload_response = client.post(
                f"/api/studies/{study_id}/upload",
                headers=headers,
                files={"file": ("chest.png", handle, "image/png")},
            )
        assert upload_response.status_code == 200
        assert upload_response.json()["status"] == "ready_for_analysis"

        ai_response = client.post(
            f"/api/studies/{study_id}/ai/run",
            headers=headers,
            json={"wait": True, "auto": False},
        )
        assert ai_response.status_code == 200
        assert ai_response.json()["status"] == "completed"
        assert "Окончательное решение принимает только врач" in ai_response.json()["disclaimer"]

        draft_response = client.post(f"/api/studies/{study_id}/report/draft", headers=headers)
        assert draft_response.status_code == 200
        assert draft_response.json()["ai_draft_text"]

        final_text = "Финальное тестовое заключение врача. AI-подсказка проверена вручную."
        save_response = client.put(
            f"/api/studies/{study_id}/report",
            headers=headers,
            json={"final_text": final_text},
        )
        assert save_response.status_code == 200
        assert save_response.json()["final_text"] == final_text

        confirm_response = client.post(
            f"/api/studies/{study_id}/report/confirm",
            headers=headers,
            json={"accept_responsibility": True},
        )
        assert confirm_response.status_code == 200
        assert confirm_response.json()["confirmed_at"]

        pdf_response = client.get(f"/api/studies/{study_id}/report/export/pdf", headers=headers)
        assert pdf_response.status_code == 200
        assert pdf_response.headers["content-type"].startswith("application/pdf")

        admin_login = client.post("/api/auth/login", json={"login": "admin", "password": "admin123"})
        admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
        audit_response = client.get("/api/audit?limit=20", headers=admin_headers)
        assert audit_response.status_code == 200
        actions = {row["action"] for row in audit_response.json()}
        assert {"login", "upload_file", "run_ai", "confirm_report", "export_report"} <= actions

    db_file = Path(os.environ["DATABASE_URL"].removeprefix("sqlite:///"))
    import gc
    gc.collect()
    import time
    time.sleep(0.3)
    if db_file.exists():
        try:
            db_file.unlink()
        except PermissionError:
            pass  # Windows: файл ещё занят, пропускаем очистку
