import asyncio
import json
import logging
import os
import re
import threading
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pydicom
from PIL import Image, ImageOps

from app.core.config import settings


LOCAL_MEDGEMMA_PROMPT = """
You are a medical imaging assistant supporting a licensed radiologist.
Analyze the provided medical image together with the clinical context.

Return only valid compact JSON with these fields:
{
  "prediction": "normal|pneumonia|pneumothorax|pleural_effusion|atelectasis",
  "confidence": 0.0,
  "top3": {"class": 0.0},
  "findings": "short imaging findings",
  "impression": "short diagnostic impression",
  "recommendations": "short next-step recommendation or need for radiologist review"
}

Use the closest prediction from the allowed set. If the image is not a chest
radiology image or is not diagnostic, say so in findings, keep confidence low,
and choose the safest closest class.
This is decision support only; do not present the output as a final diagnosis.
Do not repeat the task instructions. Do not write "Determine the ..." sections.
Do not include chain-of-thought, hidden reasoning, markdown, or explanations.
""".strip()


@dataclass
class _LoadedMedGemma:
    model: Any
    processor: Any
    torch: Any
    dtype: Any
    device_label: str
    model_source: str


_MODEL_LOCK = threading.Lock()
_LOADED: _LoadedMedGemma | None = None


def _configure_transformers_runtime() -> None:
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")
    warnings.filterwarnings(
        "ignore",
        message=r".*_check_is_size will be removed.*",
        category=FutureWarning,
    )
    logging.getLogger("torch.utils.flop_counter").setLevel(logging.ERROR)
    if settings.local_medgemma_local_files_only:
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")


def _model_source() -> str:
    path = settings.local_medgemma_model_path
    if path and path.exists():
        return str(path)
    if settings.local_medgemma_local_files_only:
        raise RuntimeError(
            "Local AI model files were not found. Install the local model files first "
            f"or set LOCAL_MEDGEMMA_MODEL_PATH. Expected: {path}"
        )
    return settings.local_medgemma_model_id


def _select_dtype(torch: Any) -> Any:
    value = settings.local_medgemma_dtype.strip().lower()
    if value == "auto":
        return torch.bfloat16 if torch.cuda.is_available() else torch.float32
    if value in {"bf16", "bfloat16"}:
        return torch.bfloat16
    if value in {"fp16", "float16"}:
        return torch.float16
    if value in {"fp32", "float32"}:
        return torch.float32
    raise RuntimeError(f"Unsupported LOCAL_MEDGEMMA_DTYPE={settings.local_medgemma_dtype!r}")


def _device_map(torch: Any) -> str | dict[str, str] | None:
    value = settings.local_medgemma_device.strip().lower()
    if value == "auto":
        return "auto" if torch.cuda.is_available() else None
    if value == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("LOCAL_MEDGEMMA_DEVICE=cuda, but CUDA is not available to torch.")
        return "auto"
    if value == "cpu":
        return {"": "cpu"}
    return value


def _load_model() -> _LoadedMedGemma:
    global _LOADED
    if _LOADED is not None:
        return _LOADED

    with _MODEL_LOCK:
        if _LOADED is not None:
            return _LOADED

        _configure_transformers_runtime()
        import torch
        from transformers import AutoModelForImageTextToText, AutoProcessor
        from transformers.utils import logging as transformers_logging

        transformers_logging.disable_progress_bar()
        transformers_logging.set_verbosity_error()

        model_source = _model_source()
        dtype = _select_dtype(torch)
        kwargs: dict[str, Any] = {
            "dtype": dtype,
            "local_files_only": settings.local_medgemma_local_files_only,
        }
        device_map = _device_map(torch)
        if device_map is not None:
            kwargs["device_map"] = device_map
        if settings.local_medgemma_load_in_4bit:
            from transformers import BitsAndBytesConfig

            kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=dtype,
                bnb_4bit_quant_type="nf4",
            )

        model = AutoModelForImageTextToText.from_pretrained(model_source, **kwargs)
        if device_map is None:
            model = model.to("cpu")
        model.eval()
        processor = AutoProcessor.from_pretrained(
            model_source,
            local_files_only=settings.local_medgemma_local_files_only,
        )
        device_label = "cuda" if torch.cuda.is_available() and settings.local_medgemma_device != "cpu" else "cpu"
        _LOADED = _LoadedMedGemma(model, processor, torch, dtype, device_label, model_source)
        return _LOADED


def _normalize_pixels(pixels: np.ndarray, invert: bool = False) -> Image.Image:
    while pixels.ndim > 2 and pixels.shape[-1] not in {3, 4}:
        pixels = pixels[pixels.shape[0] // 2]
    if pixels.ndim == 3 and pixels.shape[-1] in {3, 4}:
        return Image.fromarray(pixels.astype(np.uint8)).convert("RGB")

    pixels = pixels.astype(np.float32)
    pixels -= float(np.min(pixels))
    maximum = float(np.max(pixels))
    if maximum > 0:
        pixels /= maximum
    pixels *= 255.0
    if invert:
        pixels = 255.0 - pixels
    return Image.fromarray(pixels.astype(np.uint8)).convert("RGB")


def _load_image(path: Path) -> Image.Image:
    suffix = path.suffix.lower()
    if suffix in {".dcm", ".dicom"}:
        dataset = pydicom.dcmread(path, force=True)
        if not hasattr(dataset, "PixelData"):
            raise RuntimeError("DICOM file does not contain PixelData.")
        try:
            from pydicom.pixel_data_handlers.util import apply_voi_lut

            pixels = apply_voi_lut(dataset.pixel_array, dataset)
        except Exception:
            pixels = dataset.pixel_array
        invert = getattr(dataset, "PhotometricInterpretation", "") == "MONOCHROME1"
        image = _normalize_pixels(np.asarray(pixels), invert=invert)
    else:
        with Image.open(path) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")

    max_side = settings.local_medgemma_max_image_side
    if max_side > 0:
        image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    return image


def _json_from_text(text: str) -> dict[str, Any] | None:
    decoder = json.JSONDecoder()
    candidates = [text.strip()]
    if "```" in text:
        parts = text.split("```")
        candidates.extend(part.strip().removeprefix("json").strip() for part in parts)
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


def _final_answer(text: str) -> str:
    marker = re.search(r"<unused\d+>\s*answer\s*", text, flags=re.IGNORECASE)
    if marker:
        return text[marker.end() :].strip()
    marker = re.search(r"(?:^|\n)\s*answer\s*:\s*", text, flags=re.IGNORECASE)
    if marker:
        return text[marker.end() :].strip()
    return text.strip()


def _section(text: str, start: str, stops: list[str]) -> str | None:
    match = re.search(rf"(?:^|\n)\s*{re.escape(start)}\s*:\s*", text, flags=re.IGNORECASE)
    if not match:
        return None
    upper = text.upper()
    content_start = match.end()
    content_end = len(text)
    for stop in stops:
        stop_match = re.search(rf"(?:^|\n)\s*{re.escape(stop)}\s*:\s*", upper[content_start:])
        if stop_match:
            content_end = min(content_end, content_start + stop_match.start())
    value = text[content_start:content_end].strip(" :-\n\t")
    return value or None


def _has_positive_term(text: str, term: str) -> bool:
    index = text.find(term)
    while index >= 0:
        prefix = text[max(0, index - 28) : index]
        if not any(marker in prefix for marker in ("no ", "without ", "negative for ", "absence of ")):
            return True
        index = text.find(term, index + len(term))
    return False


def _fallback_payload_from_report(text: str) -> dict[str, Any]:
    lower = text.casefold()
    prediction: str | None = None
    if any(
        phrase in lower
        for phrase in (
            "no acute cardiopulmonary",
            "lungs are clear",
            "clear lungs",
            "no focal airspace",
            "no focal consolidation",
        )
    ):
        prediction = "normal"
    elif _has_positive_term(lower, "pneumothorax"):
        prediction = "pneumothorax"
    elif _has_positive_term(lower, "pleural effusion") or _has_positive_term(lower, "effusion"):
        prediction = "pleural_effusion"
    elif _has_positive_term(lower, "pneumonia") or _has_positive_term(lower, "consolidation"):
        prediction = "pneumonia"
    elif _has_positive_term(lower, "atelectasis"):
        prediction = "atelectasis"
    elif "normal" in lower:
        prediction = "normal"

    if not prediction:
        return {}

    findings = _section(text, "FINDINGS", ["IMPRESSION", "CONCLUSION"])
    impression = _section(text, "IMPRESSION", ["RECOMMENDATION", "RECOMMENDATIONS"])
    return {
        "prediction": prediction,
        "confidence": 0.0,
        "top3": {},
        "findings": findings or text,
        "impression": impression or "",
        "warning": "Local AI did not return numeric confidence; the generated text was preserved for clinician review.",
    }


def _numeric_confidence(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    if numeric > 1.0:
        numeric /= 100.0
    return max(0.0, min(1.0, numeric))


def _ensure_estimated_confidence(payload: dict[str, Any], text: str) -> dict[str, Any]:
    if _numeric_confidence(payload.get("confidence")) > 0:
        return payload
    prediction = str(payload.get("prediction") or "").strip()
    allowed = {"normal", "pneumonia", "pneumothorax", "pleural_effusion", "atelectasis"}
    probabilities = payload.get("top3")
    if isinstance(probabilities, dict):
        parsed_probabilities = {str(key): _numeric_confidence(value) for key, value in probabilities.items()}
        if prediction in parsed_probabilities and parsed_probabilities[prediction] > 0:
            payload["confidence"] = parsed_probabilities[prediction]
            payload["top3"] = parsed_probabilities
            return payload
        best = max(parsed_probabilities.values(), default=0.0)
        if best > 0:
            payload["confidence"] = best
            payload["top3"] = parsed_probabilities
            return payload

    if prediction not in allowed:
        fallback = _fallback_payload_from_report(text)
        prediction = str(fallback.get("prediction") or "").strip()
        if prediction in allowed:
            payload.setdefault("prediction", prediction)
            payload.setdefault("findings", fallback.get("findings"))
            payload.setdefault("impression", fallback.get("impression"))
        else:
            payload.setdefault("confidence", 0.0)
            payload.setdefault("top3", {})
            payload["warning"] = "Local AI did not return a usable class or numeric confidence."
            return payload

    if not isinstance(payload.get("top3"), dict):
        payload["top3"] = {}
    payload["confidence"] = 0.0
    payload["warning"] = (
        "Local AI did not return numeric confidence; the generated text was preserved for clinician review."
    )
    return payload


def _language_name(lang: str | None) -> str:
    value = (lang or "ru").strip().lower()
    if value.startswith("kk"):
        return "Kazakh"
    if value.startswith("en"):
        return "English"
    return "Russian"


def _messages(
    image: Image.Image,
    clinical_note: str | None,
    study_type: str | None,
    lang: str | None = None,
) -> list[dict[str, Any]]:
    language = _language_name(lang)
    context = (
        f"{LOCAL_MEDGEMMA_PROMPT}\n\n"
        f"Write the values of findings, impression, and recommendations in {language}. "
        "Keep JSON field names in English.\n"
        f"Study type: {study_type or 'not provided'}\n"
        f"Clinical note: {clinical_note or 'not provided'}"
    )
    return [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": context},
            ],
        }
    ]


def _generate_sync(
    image_path: str,
    clinical_note: str | None,
    study_type: str | None,
    lang: str | None = None,
) -> dict[str, Any]:
    loaded = _load_model()
    image = _load_image(Path(image_path))
    messages = _messages(image, clinical_note, study_type, lang)
    inputs = loaded.processor.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    )
    target_device = loaded.model.device
    if loaded.device_label == "cuda":
        inputs = inputs.to(target_device, dtype=loaded.dtype)
    else:
        inputs = inputs.to(target_device)

    input_len = inputs["input_ids"].shape[-1]
    tokenizer = getattr(loaded.processor, "tokenizer", None)
    generation_config = getattr(loaded.model, "generation_config", None)
    eos_token_id = getattr(tokenizer, "eos_token_id", None) or getattr(generation_config, "eos_token_id", None)
    pad_token_id = (
        getattr(tokenizer, "pad_token_id", None)
        or getattr(generation_config, "pad_token_id", None)
        or eos_token_id
    )
    generation_kwargs: dict[str, Any] = {
        "max_new_tokens": settings.local_medgemma_max_new_tokens,
        "do_sample": False,
    }
    if pad_token_id is not None:
        generation_kwargs["pad_token_id"] = pad_token_id
    if eos_token_id is not None:
        generation_kwargs["eos_token_id"] = eos_token_id
    with loaded.torch.inference_mode():
        output = loaded.model.generate(
            **inputs,
            **generation_kwargs,
        )
    decoded_raw = loaded.processor.decode(output[0][input_len:], skip_special_tokens=True).strip()
    decoded = _final_answer(decoded_raw)
    payload = _json_from_text(decoded) or _fallback_payload_from_report(decoded)
    payload = _ensure_estimated_confidence(payload, decoded)
    payload.update(
        {
            "response": decoded,
            "raw_generation": decoded_raw if decoded_raw != decoded else None,
            "mode": "local_ai",
            "model": "local_ai",
            "model_source": loaded.model_source,
            "device": loaded.device_label,
            "clinical_note_used": bool(clinical_note),
        }
    )
    return payload


async def run_local_medgemma_inference(
    image_path: str,
    clinical_note: str | None = None,
    study_type: str | None = None,
    lang: str | None = None,
) -> dict[str, Any]:
    return await asyncio.to_thread(_generate_sync, image_path, clinical_note, study_type, lang)
