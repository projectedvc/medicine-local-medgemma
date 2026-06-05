import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from app.core.config import settings
from app.models.enums import FindingClass


@dataclass
class NormalizedAIResult:
    predicted_class: FindingClass | None
    raw_predicted_label: str | None
    confidence: float
    probabilities: dict[str, float]
    raw_response: dict[str, Any]
    warning: str | None = None
    heatmap_path: str | None = None


LABEL_MAP = {
    "normal": FindingClass.normal,
    "norm": FindingClass.normal,
    "no finding": FindingClass.normal,
    "норма": FindingClass.normal,
    "pneumonia": FindingClass.pneumonia,
    "infiltration": FindingClass.pneumonia,
    "пневмония": FindingClass.pneumonia,
    "инфильтрация": FindingClass.pneumonia,
    "pleural effusion": FindingClass.pleural_effusion,
    "effusion": FindingClass.pleural_effusion,
    "выпот": FindingClass.pleural_effusion,
    "плевральный выпот": FindingClass.pleural_effusion,
    "гидроторакс": FindingClass.pleural_effusion,
    "pneumothorax": FindingClass.pneumothorax,
    "пневмоторакс": FindingClass.pneumothorax,
    "atelectasis": FindingClass.atelectasis,
    "ателектаз": FindingClass.atelectasis,
}


def _parse_confidence(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, str):
        value = value.strip().replace("%", "").replace(",", ".")
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    if numeric > 1.0:
        numeric /= 100.0
    return max(0.0, min(1.0, numeric))


def _normalize_label(label: Any) -> tuple[FindingClass | None, str | None]:
    if label is None:
        return None, None
    raw = str(label).strip()
    normalized = raw.casefold()
    return LABEL_MAP.get(normalized), raw


def _normalize_probabilities(raw: Any) -> dict[str, float]:
    if not isinstance(raw, dict):
        return {}
    result: dict[str, float] = {}
    for key, value in raw.items():
        result[str(key)] = _parse_confidence(value)
    return result


def normalize_ai_response(payload: dict[str, Any]) -> NormalizedAIResult:
    label = payload.get("prediction") or payload.get("class") or payload.get("label")
    predicted_class, raw_label = _normalize_label(label)
    confidence = _parse_confidence(payload.get("confidence") or payload.get("score") or payload.get("probability"))
    probabilities = _normalize_probabilities(payload.get("top3") or payload.get("probabilities") or payload.get("scores"))
    return NormalizedAIResult(
        predicted_class=predicted_class,
        raw_predicted_label=raw_label,
        confidence=confidence,
        probabilities=probabilities,
        raw_response=payload,
        warning=payload.get("warning"),
        heatmap_path=payload.get("heatmap_path") or payload.get("heatmap_url"),
    )


def _mock_ai_result(file_path: Path) -> NormalizedAIResult:
    data = file_path.read_bytes()
    digest = hashlib.sha256(data).digest()
    classes = list(FindingClass)
    predicted = classes[digest[0] % len(classes)]
    confidence = 0.55 + (digest[1] % 40) / 100.0
    confidence = min(confidence, 0.94)
    probabilities = {item.value: 0.08 for item in classes}
    probabilities[predicted.value] = confidence
    raw = {
        "prediction": predicted.value,
        "confidence": confidence,
        "probabilities": probabilities,
        "mode": "mock",
    }
    return NormalizedAIResult(
        predicted_class=predicted,
        raw_predicted_label=predicted.value,
        confidence=confidence,
        probabilities=probabilities,
        raw_response=raw,
        warning="AI_SERVICE_URL не задан или недоступен: использован демонстрационный mock-ответ.",
    )


async def run_ai_inference(file_path: str) -> NormalizedAIResult:
    path = Path(file_path)
    if settings.ai_service_url:
        url = settings.ai_service_url.rstrip("/")
        predict_url = url if url.endswith(("/predict", "/analyze")) else f"{url}/predict"
        try:
            async with httpx.AsyncClient(timeout=settings.ai_timeout_seconds) as client:
                with path.open("rb") as handle:
                    response = await client.post(
                        predict_url,
                        files={"file": (path.name, handle, "application/octet-stream")},
                    )
            response.raise_for_status()
            return normalize_ai_response(response.json())
        except Exception as exc:
            if not settings.ai_allow_mock:
                raise RuntimeError(f"AI-сервис недоступен: {exc}") from exc
            result = _mock_ai_result(path)
            result.warning = f"AI-сервис недоступен ({exc}); показан demo-ответ."
            return result

    if settings.ai_allow_mock:
        return _mock_ai_result(path)
    raise RuntimeError("AI_SERVICE_URL не задан, а AI_ALLOW_MOCK=false.")


def probabilities_to_json(probabilities: dict[str, float]) -> str:
    return json.dumps(probabilities, ensure_ascii=False)
