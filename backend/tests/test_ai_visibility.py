import asyncio
from types import SimpleNamespace

from app.api.routes import ai as ai_routes
from app.models.enums import FindingClass
from app.services.ai_client import AIResult


class _FakeSession:
    def commit(self):
        return None

    def refresh(self, _value):
        return None


def test_selected_model_result_is_visible_even_with_a_low_score(monkeypatch):
    async def fake_inference(*_args, **_kwargs):
        return AIResult(
            predicted_class=FindingClass.normal,
            raw_predicted_label="normal",
            confidence=0.42,
            probabilities={"normal": 0.42, "pneumonia": 0.39, "other_abnormal": 0.19},
            raw_response={"finding": "normal", "impression": "No focal pneumonia."},
        )

    monkeypatch.setattr(ai_routes, "run_ai_inference", fake_inference)
    analysis = SimpleNamespace()
    study = SimpleNamespace(
        images=[SimpleNamespace(storage_path="unused-in-test.png")],
        clinical_note=None,
        study_type="CXR",
        status=None,
    )

    result = asyncio.run(
        ai_routes.process_analysis(
            _FakeSession(),
            analysis,
            study,
            lang="ru",
            model_variant="rsna_v2",
        )
    )

    assert result.predicted_class == FindingClass.normal
    assert result.confidence == 0.42
    assert result.hidden_due_low_confidence is False
    assert "доступен для тестирования" in result.warning
