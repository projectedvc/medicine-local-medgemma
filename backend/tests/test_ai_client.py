from app.models.enums import FindingClass
from app.services.ai_client import GENERATE_PROMPT, _candidate_endpoints, normalize_ai_response


def test_generate_response_extracts_structured_json():
    result = normalize_ai_response(
        {
            "response": (
                'Assistant answer:\n{"prediction":"pneumonia","confidence":0.88,'
                '"top3":{"pneumonia":0.88,"normal":0.09,"pleural_effusion":0.03}}'
            )
        }
    )

    assert result.predicted_class == FindingClass.pneumonia
    assert result.raw_predicted_label == "pneumonia"
    assert result.confidence == 0.88
    assert result.probabilities["pneumonia"] == 0.88


def test_generate_response_plain_text_fallback():
    result = normalize_ai_response({"response": "Likely pneumothorax. Confidence: 82%."})

    assert result.predicted_class == FindingClass.pneumothorax
    assert result.raw_predicted_label == "pneumothorax"
    assert result.confidence == 0.82
    assert result.probabilities == {"pneumothorax": 0.82}


def test_candidate_endpoints_support_generate_urls():
    assert _candidate_endpoints("https://example.test/generate") == [
        ("https://example.test/generate", "generate")
    ]
    assert ("https://example.test/generate", "generate") in _candidate_endpoints("https://example.test")


def test_generate_prompt_has_no_copyable_schema_placeholders():
    assert "one short clinical conclusion" not in GENERATE_PROMPT
    assert "up to three visible radiographic signs" not in GENERATE_PROMPT
    assert '"confidence":0.0' not in GENERATE_PROMPT


def test_template_values_are_not_exposed_as_clinical_text():
    result = normalize_ai_response(
        {
            "text": (
                '{"finding":"normal","confidence":0.0,"bbox":null,'
                '"impression":"one short clinical conclusion",'
                '"evidence":["up to three visible radiographic signs"]}'
            )
        }
    )

    assert result.predicted_class == FindingClass.normal
    assert result.confidence == 0.0
    assert result.raw_response["impression"] is None
    assert result.raw_response["evidence"] == []


def test_not_diagnostic_cannot_keep_a_high_confidence():
    result = normalize_ai_response(
        {"finding": "not_diagnostic", "confidence": 0.85, "impression": "Недостаточно данных."}
    )

    assert result.predicted_class is None
    assert result.confidence == 0.0
    assert result.probabilities == {}


def test_class_only_model_does_not_publish_generated_coordinates():
    result = normalize_ai_response(
        {
            "finding": "pneumonia",
            "confidence": 0.91,
            "bbox": [0.1, 0.2, 0.8, 0.9],
            "impression": "Признаки пневмонии.",
        }
    )

    assert result.raw_response["localization"] == {
        "validated": False,
        "source": None,
        "bbox": None,
        "reason": "missing_localization_provenance",
    }


def test_test_gated_localization_is_preserved():
    result = normalize_ai_response(
        {
            "finding": "pneumonia",
            "confidence": 0.91,
            "localization": {
                "validated": True,
                "source": "medai-rsna-pneumonia-v2:test-gated-boxes",
                "bbox": [0.1, 0.2, 0.8, 0.9],
            },
        }
    )

    assert result.raw_response["localization"]["validated"] is True
    assert result.raw_response["localization"]["bbox"] == [0.1, 0.2, 0.8, 0.9]


def test_rsna_other_abnormal_is_a_supported_triage_class():
    result = normalize_ai_response(
        {"finding": "other_abnormal", "confidence": 0.86, "impression": "Другая патология."}
    )

    assert result.predicted_class == FindingClass.other_abnormal
    assert result.confidence == 0.86


def test_absolute_pixel_bbox_is_rejected():
    result = normalize_ai_response(
        {"finding": "pneumonia", "confidence": 0.9, "bbox": [78, 28, 934, 733]}
    )

    assert result.raw_response["bbox"] is None
