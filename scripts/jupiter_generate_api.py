"""Jupyter GPU inference API for MedAI base and fine-tuned variants."""

from __future__ import annotations

import base64
import io
import json
import re
import threading
from contextlib import nullcontext
from pathlib import Path
from typing import Any

import torch
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

BASE_MODEL_ID = "google/medgemma-1.5-4b-it"
DEFAULT_ADAPTER_PATH = Path(
    "/home/jovyan/work/medgemma_finetune/runs/cxr_pneumonia_v1/"
    "bf16_lora_baseline/final_adapter"
)
ADAPTER_NAME = "pneumonia_v1"
MODEL_LABELS = {"base": "medai-base", "pneumonia_v1": "medai-pneumonia-v1"}
DEFAULT_PROMPT = """Внимательно оцените саму рентгенограмму грудной клетки.
Выберите один класс: normal, pneumonia или not_diagnostic. Верните только JSON с полями
finding, confidence, impression и evidence. confidence — числовая уверенность по этому
снимку от 0.01 до 0.99; значение 0 допустимо только для нечитаемого снимка.
impression — фактическое краткое заключение на русском по этому пациенту, evidence — реально
видимые признаки. Не копируйте инструкцию, описания полей, шаблоны или примеры."""

_PLACEHOLDER_TEXTS = {
    "one short clinical conclusion",
    "up to three visible radiographic signs",
    "краткое врачебное заключение",
    "до 3 кратких признаков",
}


def _is_placeholder_text(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    normalized = re.sub(r"\s+", " ", value).strip().casefold().strip(" .:_-")
    return normalized in _PLACEHOLDER_TEXTS

app = FastAPI(title="MedAI GPU API", version="2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
_runtime: dict[str, Any] = {
    "model": None,
    "processor": None,
    "adapter_available": False,
    "device": None,
}
_generation_lock = threading.Lock()


def _decode_image(value: str) -> Image.Image:
    if not value:
        raise HTTPException(status_code=422, detail="image_base64 is required")
    if "," in value and value.lstrip().startswith("data:"):
        value = value.split(",", 1)[1]
    try:
        return Image.open(io.BytesIO(base64.b64decode(value))).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Invalid image data") from exc


def _extract_json_object(text: str) -> dict[str, Any] | None:
    """Return the first complete JSON object, ignoring prose and trailing braces."""
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def _unwrap_result(obj: dict[str, Any]) -> dict[str, Any]:
    """Unwrap JSON that a model accidentally returned inside a wrapper field."""
    current = obj
    for _ in range(3):
        nested_text = next(
            (
                current.get(key)
                for key in ("impression", "response", "text")
                if isinstance(current.get(key), str) and "{" in current.get(key, "")
            ),
            None,
        )
        if not nested_text:
            break
        nested = _extract_json_object(nested_text)
        if not nested or not any(
            key in nested for key in ("finding", "prediction", "confidence", "impression", "evidence")
        ):
            break
        current = nested
    return current


def _clean_model_text(text: str) -> str:
    fence = chr(96) * 3
    cleaned = text.strip().replace(fence + "json", "").replace(fence, "").strip()
    obj = _extract_json_object(cleaned)

    if obj is None:
        compact = re.sub(r"\s+", " ", cleaned)
        # Do not forward prompts, markup, or long model chatter into a medical report.
        if "{" in compact or len(compact) > 240:
            compact = "Недостаточно данных для заключения."
        result = {
            "finding": "not_diagnostic",
            "confidence": 0.0,
            "bbox": None,
            "impression": compact or "Недостаточно данных для заключения.",
            "evidence": [],
        }
        return json.dumps(result, ensure_ascii=False, separators=(",", ":"))

    obj = _unwrap_result(obj)
    raw_finding = str(obj.get("finding", obj.get("prediction", "not_diagnostic"))).strip().casefold()
    aliases = {
        "no finding": "normal",
        "no_finding": "normal",
        "negative": "normal",
        "not diagnostic": "not_diagnostic",
        "not-diagnostic": "not_diagnostic",
        "pneumothorax": "pneumothorax",
        "pleural effusion": "pleural_effusion",
    }
    finding = aliases.get(raw_finding, raw_finding.replace(" ", "_"))
    if finding not in {
        "normal", "pneumonia", "pneumothorax", "pleural_effusion", "atelectasis", "not_diagnostic"
    }:
        finding = "not_diagnostic"

    try:
        confidence = float(obj.get("confidence", 0.0))
        if 1.0 < confidence <= 100.0:
            confidence /= 100.0
        confidence = max(0.0, min(1.0, confidence))
    except (TypeError, ValueError):
        confidence = 0.0

    if finding == "not_diagnostic":
        confidence = 0.0

    # This dataset contains image-level labels, not boxes or masks. Do not
    # manufacture lesion coordinates from a generative response.
    bbox = None

    impression = re.sub(r"\s+", " ", str(obj.get("impression") or "")).strip()
    generic_impression = impression.casefold().strip(" .:_-").replace(" ", "_")
    if (
        "{" in impression
        or '"finding"' in impression
        or len(impression) > 300
        or _is_placeholder_text(impression)
        or generic_impression in {
            "normal", "pneumonia", "pneumothorax", "pleural_effusion", "atelectasis", "not_diagnostic"
        }
    ):
        impression = ""
    if not impression:
        impression = {
            "normal": "Острой патологии не выявлено.",
            "pneumonia": "Рентгенологические признаки пневмонии.",
            "pneumothorax": "Рентгенологические признаки пневмоторакса.",
            "pleural_effusion": "Рентгенологические признаки плеврального выпота.",
            "atelectasis": "Рентгенологические признаки ателектаза.",
            "not_diagnostic": "Недостаточно данных для заключения.",
        }[finding]

    raw_evidence = obj.get("evidence", [])
    evidence: list[str] = []
    if isinstance(raw_evidence, list):
        for item in raw_evidence:
            value = re.sub(r"\s+", " ", str(item)).strip()
            if value and "{" not in value and not _is_placeholder_text(value) and value not in evidence:
                evidence.append(value[:220])
            if len(evidence) == 3:
                break

    result = {
        "finding": finding,
        "confidence": round(confidence, 4),
        "bbox": bbox,
        "localization": {
            "validated": False,
            "source": None,
            "bbox": None,
            "reason": "class_only_training_data",
        },
        "impression": impression[:300],
        "evidence": evidence,
    }
    return json.dumps(result, ensure_ascii=False, separators=(",", ":"))


def _select_adapter(model: Any, model_variant: str):
    if model_variant == "base":
        disable = getattr(model, "disable_adapter", None)
        return disable() if callable(disable) else nullcontext()
    if model_variant != ADAPTER_NAME:
        raise HTTPException(status_code=422, detail="Unknown model_variant")
    if not _runtime["adapter_available"]:
        raise HTTPException(status_code=503, detail="Fine-tuned model is unavailable")
    set_adapter = getattr(model, "set_adapter", None)
    if callable(set_adapter):
        set_adapter(ADAPTER_NAME)
    return nullcontext()


def _model_device(model: Any) -> torch.device:
    try:
        return next(model.parameters()).device
    except (StopIteration, AttributeError):
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")


@app.get("/health")
def health() -> dict[str, Any]:
    ready = _runtime["model"] is not None and _runtime["processor"] is not None
    return {
        "status": "ok" if ready else "loading",
        "ready": ready,
        "device": str(_runtime["device"]) if _runtime["device"] else None,
        "adapter_available": bool(_runtime["adapter_available"]),
        "model_variants": [
            {"id": "pneumonia_v1", "label": MODEL_LABELS["pneumonia_v1"], "available": bool(_runtime["adapter_available"])},
            {"id": "base", "label": MODEL_LABELS["base"], "available": ready},
        ],
    }

@app.post("/generate")
async def generate(request: Request) -> dict[str, Any]:
    model = _runtime["model"]
    processor = _runtime["processor"]
    if model is None or processor is None:
        raise HTTPException(status_code=503, detail="Model is still loading")

    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        image_value = body.get("image_base64", "")
        prompt = body.get("prompt") or DEFAULT_PROMPT
        model_variant = body.get("model_variant") or "base"
    else:
        form = await request.form()
        prompt = str(form.get("prompt") or DEFAULT_PROMPT)
        model_variant = str(form.get("model_variant") or "base")
        upload = form.get("file")
        if upload is None:
            raise HTTPException(status_code=422, detail="file is required")
        image_value = base64.b64encode(await upload.read()).decode("ascii")

    if str(model_variant) not in MODEL_LABELS:
        raise HTTPException(status_code=422, detail="Unknown model_variant")

    image = _decode_image(str(image_value))
    messages = [{
        "role": "user",
        "content": [
            {"type": "image", "image": image},
            {"type": "text", "text": str(prompt)},
        ],
    }]
    inputs = processor.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    )
    device = _model_device(model)
    inputs = {
        key: value.to(device) if hasattr(value, "to") else value
        for key, value in inputs.items()
    }
    prompt_tokens = inputs["input_ids"].shape[-1]

    with _generation_lock:
        adapter_context = _select_adapter(model, str(model_variant))
        with adapter_context, torch.inference_mode():
            output = model.generate(
                **inputs,
                max_new_tokens=192,
                do_sample=False,
                use_cache=True,
            )

    generated = output[0][prompt_tokens:]
    raw_text = processor.decode(generated, skip_special_tokens=True)
    return {
        "text": _clean_model_text(raw_text),
        "model_variant": str(model_variant),
        "model_version": MODEL_LABELS[str(model_variant)],
    }


def configure_runtime(model: Any, processor: Any, adapter_available: bool) -> None:
    model.eval()
    _runtime.update(
        model=model,
        processor=processor,
        adapter_available=adapter_available,
        device=_model_device(model),
    )


def start_api(
    model: Any,
    processor: Any,
    adapter_available: bool,
    host: str = "0.0.0.0",
    port: int = 8005,
):
    configure_runtime(model, processor, adapter_available)
    thread = threading.Thread(
        target=uvicorn.run,
        kwargs={"app": app, "host": host, "port": port, "log_level": "info"},
        daemon=True,
        name="medai-gpu-api",
    )
    thread.start()
    return thread


def load_and_start_api(
    adapter_path: str | Path = DEFAULT_ADAPTER_PATH,
    host: str = "0.0.0.0",
    port: int = 8005,
    local_files_only: bool = True,
):
    from peft import PeftModel
    from transformers import AutoModelForImageTextToText, AutoProcessor

    adapter_path = Path(adapter_path)
    weights = adapter_path / "adapter_model.safetensors"
    if not weights.exists():
        raise FileNotFoundError(f"Adapter weights not found: {adapter_path}")

    processor = AutoProcessor.from_pretrained(
        BASE_MODEL_ID,
        local_files_only=local_files_only,
    )
    base_model = AutoModelForImageTextToText.from_pretrained(
        BASE_MODEL_ID,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        local_files_only=local_files_only,
    )
    model = PeftModel.from_pretrained(
        base_model,
        adapter_path,
        adapter_name=ADAPTER_NAME,
        is_trainable=False,
    )
    thread = start_api(
        model,
        processor,
        adapter_available=True,
        host=host,
        port=port,
    )
    return model, processor, thread


if __name__ == "__main__":
    loaded_model, loaded_processor, api_thread = load_and_start_api()
    api_thread.join()
