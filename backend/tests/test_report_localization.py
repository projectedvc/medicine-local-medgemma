import json

import pytest

from app.core.config import settings
from app.models.ai import AIAnalysis
from app.models.enums import AIJobStatus, FindingClass
from app.models.report import Report
from app.models.study import Study
from app.services import report_localization
from app.services.report_localization import build_localized_ai_draft
from app.services.reporting import _report_text_for_lang


@pytest.fixture(autouse=True)
def use_local_translation_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "translation_provider", "local")


@pytest.fixture()
def study() -> Study:
    return Study(
        accession_number="RX-TEST",
        patient_code="P-001",
        study_type="CXR",
        clinical_note="cough",
        uploader_id=1,
    )


@pytest.fixture()
def analysis() -> AIAnalysis:
    return AIAnalysis(
        study_id=1,
        requested_by_id=1,
        status=AIJobStatus.completed,
        predicted_class=FindingClass.pneumonia,
        confidence=0.83,
        threshold=0.5,
        hidden_due_low_confidence=False,
        model_version="local-ai",
        dataset_version="local",
    )


@pytest.mark.parametrize(
    ("lang", "heading", "finding"),
    [
        ("kk", "Сипаттама:", "Пневмония"),
        ("ru", "Описание:", "пневмония"),
        ("en", "Findings:", "Pneumonia"),
    ],
)
def test_ai_draft_is_localized(lang: str, heading: str, finding: str, study: Study, analysis: AIAnalysis) -> None:
    text = build_localized_ai_draft(study, analysis, lang)

    assert heading in text
    assert finding in text
    assert "Уверенность AI" not in text
    assert "RX-TEST" not in text


def test_ai_draft_prefers_local_ai_generated_text(study: Study, analysis: AIAnalysis) -> None:
    analysis.predicted_class = None
    analysis.confidence = 0.0
    analysis.hidden_due_low_confidence = True
    analysis.raw_response_json = json.dumps(
        {
            "response": (
                "MedGemMA local response:\n"
                "Findings: Live model finding.\n"
                "Impression: Live model impression.\n"
                "Recommendations: Live model recommendation."
            )
        }
    )

    text = build_localized_ai_draft(study, analysis, "en")

    assert "Live model finding." in text
    assert "Live model impression." in text
    assert "Live model recommendation." in text
    assert "MedGemMA" not in text


def test_ai_draft_translates_generated_text_to_russian(study: Study, analysis: AIAnalysis) -> None:
    analysis.predicted_class = FindingClass.normal
    analysis.confidence = 0.71
    analysis.hidden_due_low_confidence = False
    analysis.raw_response_json = json.dumps(
        {
            "findings": "The image shows a normal chest x-ray. No obvious abnormalities are visible.",
            "impression": "No acute cardiopulmonary abnormality.",
            "recommendations": "No further imaging is required.",
        }
    )

    text = build_localized_ai_draft(study, analysis, "ru")

    assert "нормальная рентгенограмма грудной клетки" in text
    assert "явных патологических изменений не видно" in text
    assert "дополнительная визуализация не требуется" in text
    assert "The image shows" not in text


def test_ai_draft_translates_generated_text_to_kazakh(study: Study, analysis: AIAnalysis) -> None:
    analysis.predicted_class = FindingClass.normal
    analysis.confidence = 0.71
    analysis.hidden_due_low_confidence = False
    analysis.raw_response_json = json.dumps(
        {
            "findings": "The image shows a normal chest x-ray. No obvious abnormalities are visible.",
            "impression": "No acute cardiopulmonary abnormality.",
            "recommendations": "No further imaging is required.",
        }
    )

    text = build_localized_ai_draft(study, analysis, "kk")

    assert "кеуде қуысының қалыпты рентгенограммасы" in text
    assert "айқын патологиялық өзгерістер көрінбейді" in text
    assert "қосымша визуализация қажет емес" in text
    assert "The image shows" not in text


def test_export_text_relocalizes_completed_analysis_for_kazakh(study: Study, analysis: AIAnalysis) -> None:
    analysis.predicted_class = FindingClass.normal
    analysis.confidence = 0.71
    analysis.hidden_due_low_confidence = False
    analysis.raw_response_json = json.dumps(
        {
            "findings": "The lungs are clear.",
            "impression": "No acute cardiopulmonary abnormality.",
            "recommendations": "No further imaging is required.",
        }
    )
    report = Report(
        study_id=1,
        ai_draft_text="AI-черновик заключения\nОписание:\nЛегкие чистые.",
        final_text="AI-черновик заключения\nОписание:\nЛегкие чистые.",
    )

    text = _report_text_for_lang(study, report, analysis, "kk")

    assert "өкпе" in text.casefold()
    assert "қосымша визуализация қажет емес" in text
    assert "Легкие чистые" not in text
    assert "The lungs are clear" not in text
    assert "The " not in text


def test_ai_draft_uses_online_translation_when_available(
    study: Study,
    analysis: AIAnalysis,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    analysis.predicted_class = FindingClass.normal
    analysis.confidence = 0.71
    analysis.hidden_due_low_confidence = False
    analysis.raw_response_json = json.dumps({"findings": "The lungs are clear."})

    def fake_translate(text: str, target_lang: str) -> str | None:
        assert target_lang == "ru"
        assert text == "The lungs are clear."
        return "Легкие без инфильтративных изменений."

    monkeypatch.setattr(report_localization, "translate_text", fake_translate)

    text = build_localized_ai_draft(study, analysis, "ru")

    assert "Легкие без инфильтративных изменений." in text
    assert "The lungs are clear" not in text


def test_ai_draft_removes_instruction_noise(study: Study, analysis: AIAnalysis) -> None:
    analysis.predicted_class = None
    analysis.confidence = 0.5
    analysis.hidden_due_low_confidence = True
    analysis.raw_response_json = json.dumps(
        {
            "findings": (
                "Determine the prediction:** Based on the image, the diagnosis is pneumonia. "
                "Determine the confidence:** The confidence is low. "
                "Determine the description:** The image shows increased opacity in the left lung. "
                "Determine the conclusion:** Findings are suspicious for pneumonia. "
                "Determine the recommendations:** Radiologist review is recommended."
            )
        }
    )

    text = build_localized_ai_draft(study, analysis, "ru")

    assert "Determine the" not in text
    assert "prediction" not in text.casefold()
    assert "затемнение" in text or "opacity" not in text


def test_ai_draft_keeps_only_clinical_sections_from_reasoning_dump(study: Study, analysis: AIAnalysis) -> None:
    analysis.predicted_class = None
    analysis.confidence = 0.03
    analysis.hidden_due_low_confidence = True
    analysis.raw_response_json = json.dumps(
        {
            "findings": (
                "<unused94>thought\nThe user wants JSON output.\n"
                "5. Determine the findings: The findings should be a short description of the image. "
                '"The chest X-ray shows clear lung fields, normal heart size, and no obvious signs of '
                'consolidation, pleural effusion, or pneumothorax."\n'
                "6. Determine the impression: The impression should be a short diagnostic impression. "
                '"The chest X-ray is unremarkable."\n'
                "7. Determine the recommendations: The recommendation should be a short next-step recommendation. "
                '"No further imaging is required."\n'
                "8. Format the output: Create the JSON structure."
            )
        }
    )

    text = build_localized_ai_draft(study, analysis, "ru")

    assert text.startswith("Описание:\n")
    assert "Заключение:" in text
    assert "Рекомендации:" in text
    assert "Легочные поля без очагово-инфильтративных изменений" in text
    assert "Рентгенограмма органов грудной клетки без острых патологических изменений" in text
    assert "JSON" not in text
    assert "Determine" not in text
    assert "долж" not in text.casefold()
    assert "Уверенность" not in text
    assert "RX-TEST" not in text
