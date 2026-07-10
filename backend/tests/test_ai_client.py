import pytest

from app.models.enums import FindingClass
from app.services.ai_client import (
    _ai_service_headers,
    _candidate_endpoints,
    normalize_ai_response,
)


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


def test_unvalidated_confidence_is_never_used_as_probability():
    result = normalize_ai_response(
        {
            "prediction": "pneumonia",
            "confidence": 0.99,
            "top3": {"pneumonia": 0.99},
            "confidence_status": "unvalidated",
            "response": '{"prediction":"pneumonia","confidence":0.99}',
        }
    )

    assert result.predicted_class == FindingClass.pneumonia
    assert result.confidence == 0.0
    assert result.probabilities == {}


def test_external_service_headers_are_server_side(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AI_SERVICE_API_KEY", "gpu-key")
    monkeypatch.setenv("AI_SERVICE_CF_ACCESS_CLIENT_ID", "client-id")
    monkeypatch.setenv("AI_SERVICE_CF_ACCESS_CLIENT_SECRET", "client-secret")

    headers = _ai_service_headers()

    assert headers["Authorization"] == "Bearer gpu-key"
    assert headers["CF-Access-Client-Id"] == "client-id"
    assert headers["CF-Access-Client-Secret"] == "client-secret"


def test_cloudflare_service_token_must_be_complete(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("AI_SERVICE_API_KEY", raising=False)
    monkeypatch.setenv("AI_SERVICE_CF_ACCESS_CLIENT_ID", "client-id")
    monkeypatch.delenv("AI_SERVICE_CF_ACCESS_CLIENT_SECRET", raising=False)

    with pytest.raises(RuntimeError, match="Both Cloudflare"):
        _ai_service_headers()


def test_candidate_endpoints_support_generate_urls():
    assert _candidate_endpoints("https://example.test/generate") == [
        ("https://example.test/generate", "generate")
    ]
    assert ("https://example.test/generate", "generate") in _candidate_endpoints("https://example.test")
