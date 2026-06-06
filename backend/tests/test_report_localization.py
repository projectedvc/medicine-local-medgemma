import json

import pytest

from app.models.ai import AIAnalysis
from app.models.enums import AIJobStatus, FindingClass
from app.models.study import Study
from app.services.report_localization import build_localized_ai_draft


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
    ("lang", "title", "finding"),
    [
        ("kk", "AI қорытынды жобасы", "Пневмония"),
        ("ru", "AI-черновик заключения", "Пневмония"),
        ("en", "AI report draft", "Pneumonia"),
    ],
)
def test_ai_draft_is_localized(lang: str, title: str, finding: str, study: Study, analysis: AIAnalysis) -> None:
    text = build_localized_ai_draft(study, analysis, lang)

    assert title in text
    assert finding in text


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
