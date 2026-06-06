import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from app.core.config import settings
from app.models.enums import FindingClass


@dataclass
class AIResult:
    predicted_class: FindingClass | None
    raw_predicted_label: str
    confidence: float
    probabilities: dict[str, float]
    raw_response: dict[str, Any]
    heatmap_path: str | None = None
    warning: str | None = None


# Backward-compatible name for older imports/tests.
NormalizedAIResult = AIResult


LABEL_MAP: dict[str, FindingClass] = {
    "normal": FindingClass.normal,
    "norm": FindingClass.normal,
    "no finding": FindingClass.normal,
    "no findings": FindingClass.normal,
    "pneumonia": FindingClass.pneumonia,
    "infiltration": FindingClass.pneumonia,
    "pleural effusion": FindingClass.pleural_effusion,
    "pleural_effusion": FindingClass.pleural_effusion,
    "effusion": FindingClass.pleural_effusion,
    "pneumothorax": FindingClass.pneumothorax,
    "atelectasis": FindingClass.atelectasis,
    "norma": FindingClass.normal,
    "пневмония": FindingClass.pneumonia,
    "плевральный выпот": FindingClass.pleural_effusion,
    "выпот": FindingClass.pleural_effusion,
    "пневмоторакс": FindingClass.pneumothorax,
    "ателектаз": FindingClass.atelectasis,
    "норма": FindingClass.normal,
}

GENERATE_PROMPT = (
    "Analyze this chest radiology image. Return only compact JSON: "
    '{"prediction":"normal|pneumonia|pneumothorax|pleural_effusion|atelectasis",'
    '"confidence":0.0,"top3":{"class":0.0}}. No extra text.'
)


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().casefold() == "true"


def _ai_service_url() -> str | None:
    return (os.environ.get("AI_SERVICE_URL") or settings.ai_service_url or "").strip() or None


def _ai_allow_mock() -> bool:
    return _env_bool("AI_ALLOW_MOCK", settings.ai_allow_mock)


def _guess_mime_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".png":
        return "image/png"
    if suffix in {".dcm", ".dicom"}:
        return "application/dicom"
    return "application/octet-stream"


def _candidate_endpoints(base_url: str) -> list[tuple[str, str]]:
    url = base_url.strip().rstrip("/")
    path = urlparse(url).path.rstrip("/").lower()
    if path.endswith("/generate"):
        return [(url, "generate")]
    return [(f"{url}/generate", "generate")]


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


def _normalize_label(label: Any) -> tuple[FindingClass | None, str]:
    if label is None:
        return None, ""
    raw = str(label).strip()
    normalized = raw.casefold().replace("-", " ").replace("_", " ")
    compact = normalized.replace(" ", "_")
    return LABEL_MAP.get(normalized) or LABEL_MAP.get(compact), raw


def _normalize_probabilities(raw: Any) -> dict[str, float]:
    if not isinstance(raw, dict):
        return {}
    return {str(key): _parse_confidence(value) for key, value in raw.items()}


def _extract_json_from_text(text: str) -> dict[str, Any] | None:
    decoder = json.JSONDecoder()
    candidates = [text.strip()]
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        candidates.insert(0, fenced.group(1).strip())

    for candidate in candidates:
        for index, char in enumerate(candidate):
            if char != "{":
                continue
            try:
                value, _ = decoder.raw_decode(candidate[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                return value
    return None


def _merge_generated_payload(raw: dict[str, Any]) -> dict[str, Any]:
    response = raw.get("response")
    if isinstance(response, dict):
        return {**raw, **response}
    if isinstance(response, str):
        extracted = _extract_json_from_text(response)
        if extracted:
            return {**raw, **extracted}
    return raw


def _find_label_in_text(text: str) -> tuple[FindingClass | None, str]:
    normalized = text.casefold().replace("-", " ")
    for label, finding in LABEL_MAP.items():
        if label.casefold().replace("_", " ") in normalized:
            return finding, label
    return None, ""


def _parse_text_confidence(text: str) -> float:
    match = re.search(
        r"(?:confidence|score|probability|вероятность|уверенность)\D{0,30}(\d+(?:[.,]\d+)?\s*%?)",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        match = re.search(r"(\d+(?:[.,]\d+)?\s*%)", text)
    if not match:
        return 0.0
    return _parse_confidence(match.group(1))


def normalize_ai_response(raw: dict[str, Any]) -> AIResult:
    payload = _merge_generated_payload(raw)
    response_text = raw.get("response") if isinstance(raw.get("response"), str) else None

    label = payload.get("prediction") or payload.get("class") or payload.get("label")
    if label is None and response_text:
        predicted_class, raw_label = _find_label_in_text(response_text)
    else:
        predicted_class, raw_label = _normalize_label(label)

    confidence = _parse_confidence(payload.get("confidence") or payload.get("score") or payload.get("probability"))
    if confidence == 0.0 and response_text:
        confidence = _parse_text_confidence(response_text)

    probabilities = _normalize_probabilities(payload.get("top3") or payload.get("probabilities") or payload.get("scores"))
    if not probabilities and predicted_class and confidence > 0:
        probabilities = {predicted_class.value: confidence}

    return AIResult(
        predicted_class=predicted_class,
        raw_predicted_label=raw_label,
        confidence=confidence,
        probabilities=probabilities,
        raw_response=payload,
        heatmap_path=payload.get("heatmap_path") or payload.get("heatmap_url"),
        warning=payload.get("warning"),
    )


def _mock_ai_result(file_path: Path) -> AIResult:
    data = file_path.read_bytes()
    digest = hashlib.sha256(data).digest()
    classes = list(FindingClass)
    predicted = classes[digest[0] % len(classes)]
    confidence = min(0.55 + (digest[1] % 40) / 100.0, 0.94)
    probabilities = {item.value: 0.08 for item in classes}
    probabilities[predicted.value] = confidence
    raw = {
        "prediction": predicted.value,
        "confidence": confidence,
        "top3": probabilities,
        "mode": "mock",
    }
    return AIResult(
        predicted_class=predicted,
        raw_predicted_label=predicted.value,
        confidence=confidence,
        probabilities=probabilities,
        raw_response=raw,
        warning="AI_ALLOW_MOCK=true: returned mock AI result without calling external service.",
    )


async def _post_generate(client: httpx.AsyncClient, url: str, path: Path) -> httpx.Response:
    with path.open("rb") as handle:
        return await client.post(
            url,
            data={"prompt": GENERATE_PROMPT},
            files={"image": (path.name, handle, _guess_mime_type(path))},
            headers={"ngrok-skip-browser-warning": "true"},
        )


def _response_payload(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError:
        return {"response": response.text}
    return payload if isinstance(payload, dict) else {"response": str(payload)}


async def run_ai_inference(image_path: str) -> AIResult:
    path = Path(image_path)
    if not path.exists():
        raise RuntimeError(f"Image file does not exist: {image_path}")

    if _ai_allow_mock():
        return _mock_ai_result(path)

    base_url = _ai_service_url()
    if not base_url:
        raise RuntimeError("AI_SERVICE_URL is not set and AI_ALLOW_MOCK=false.")

    url, _ = _candidate_endpoints(base_url)[0]
    try:
        async with httpx.AsyncClient(timeout=settings.ai_timeout_seconds) as client:
            response = await _post_generate(client, url, path)
        response.raise_for_status()
    except Exception as exc:
        raise RuntimeError(f"AI service request failed: {exc}") from exc

    return normalize_ai_response(_response_payload(response))


def probabilities_to_json(probabilities: dict[str, float]) -> str:
    return json.dumps(probabilities, ensure_ascii=False)
