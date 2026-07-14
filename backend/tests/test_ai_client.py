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
