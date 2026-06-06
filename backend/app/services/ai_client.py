import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

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

GENERATE_PROMPT = (
    "Analyze this chest radiology image. Return only JSON with keys: "
    '"prediction" as one of normal, pneumonia, pleural_effusion, pneumothorax, atelectasis; '
    '"confidence" as a number from 0 to 1; '
    'and "top3" as an object of class probabilities.'
)


def _guess_mime_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".png":
        return "image/png"
    if suffix in {".dcm", ".dicom"}:
        return "application/dicom"
    return "application/octet-stream"


def _endpoint_kind(url: str) -> str | None:
    path = urlparse(url).path.rstrip("/").lower()
    if path.endswith("/generate"):
        return "generate"
    if path.endswith(("/predict", "/analyze")):
        return "file"
    return None


def _candidate_endpoints(base_url: str) -> list[tuple[str, str]]:
    url = base_url.rstrip("/")
    kind = _endpoint_kind(url)
    if kind:
        return [(url, kind)]
    return [
        (f"{url}/predict", "file"),
        (f"{url}/generate", "generate"),
        (f"{url}/analyze", "file"),
    ]


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


def _merge_generated_payload(payload: dict[str, Any]) -> dict[str, Any]:
    response = payload.get("response") or payload.get("text") or payload.get("result")
    if isinstance(response, dict):
        return {**payload, **response}
    if isinstance(response, str):
        extracted = _extract_json_from_text(response)
        if extracted:
            return {**payload, **extracted}
    return payload


def _find_label_in_text(text: str) -> tuple[FindingClass | None, str | None]:
    normalized = text.casefold()
    for label, finding in LABEL_MAP.items():
        if label and label in normalized:
            return finding, label
    return None, None


def _parse_text_confidence(text: str) -> float:
    match = re.search(
        r"(?:confidence|score|probability|вероятность|уверенность)\D{0,20}(\d+(?:[.,]\d+)?\s*%?)",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return 0.0
    return _parse_confidence(match.group(1))


def normalize_ai_response(payload: dict[str, Any]) -> NormalizedAIResult:
    payload = _merge_generated_payload(payload)
    label = payload.get("prediction") or payload.get("class") or payload.get("label")
    response_text = payload.get("response") if isinstance(payload.get("response"), str) else None
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
    return NormalizedAIResult(
        predicted_class=predicted_class,
        raw_predicted_label=raw_label,
        confidence=confidence,
        probabilities=probabilities,
        raw_response=payload,
        warning=payload.get("warning"),
        heatmap_path=payload.get("heatmap_path") or payload.get("heatmap_url"),
    )


async def _post_to_ai_service(client: httpx.AsyncClient, url: str, mode: str, path: Path) -> httpx.Response:
    mime_type = _guess_mime_type(path)
    with path.open("rb") as handle:
        if mode == "generate":
            return await client.post(
                url,
                data={"prompt": GENERATE_PROMPT},
                files={"image": (path.name, handle, mime_type)},
            )
        return await client.post(
            url,
            files={"file": (path.name, handle, mime_type)},
        )


def _response_payload(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError:
        return {"response": response.text}
    return payload if isinstance(payload, dict) else {"response": payload}


async def _call_ai_service(file_path: Path) -> NormalizedAIResult:
    assert settings.ai_service_url
    endpoints = _candidate_endpoints(settings.ai_service_url)
    last_error: Exception | None = None
    retry_statuses = {404, 405, 422}

    async with httpx.AsyncClient(timeout=settings.ai_timeout_seconds) as client:
        for url, mode in endpoints:
            try:
                response = await _post_to_ai_service(client, url, mode, file_path)
                if len(endpoints) > 1 and response.status_code in retry_statuses:
                    last_error = httpx.HTTPStatusError(
                        f"{response.status_code} from {url}",
                        request=response.request,
                        response=response,
                    )
                    continue
                response.raise_for_status()
                return normalize_ai_response(_response_payload(response))
            except Exception as exc:
                last_error = exc
                if len(endpoints) == 1:
                    break

    raise RuntimeError(f"AI service request failed: {last_error}")


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
        try:
            return await _call_ai_service(path)
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
