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
LEGACY_ADAPTER_PATH = Path(
    "/home/jovyan/work/medgemma_finetune/runs/cxr_pneumonia_v1/"
    "bf16_lora_baseline/final_adapter"
)
RSNA_V2_ADAPTER_PATH = Path(
    "/home/jovyan/work/medgemma_rsna_v2/runs/"
    "rsna_quality_full_lr4e5_1epoch_20260714/final_adapter"
)
RSNA_V2_REPORT_DIR = RSNA_V2_ADAPTER_PATH.parent.parent
RSNA_V2_TEST_REPORT = RSNA_V2_REPORT_DIR / "eval_full_test_128_loc32.json"
RSNA_V2_VALIDATION_REPORT = RSNA_V2_REPORT_DIR / "eval_full_validation_128_loc32.json"
RSNA_DETECTOR_DIR = Path("/home/jovyan/work/medgemma_rsna_v2/detector/rsna_frcnn_v1")
RSNA_DETECTOR_CHECKPOINT = RSNA_DETECTOR_DIR / "detector.pt"
RSNA_DETECTOR_REPORT = RSNA_DETECTOR_DIR / "quality_report.json"
DEFAULT_ADAPTER_PATH = LEGACY_ADAPTER_PATH
ADAPTER_PATHS = {
    "pneumonia_v1": LEGACY_ADAPTER_PATH,
    "rsna_v2": RSNA_V2_ADAPTER_PATH,
}
MODEL_LABELS = {
    "base": "medai-base",
    "pneumonia_v1": "medai-pneumonia-v1",
    "rsna_v2": "medai-1.0",
}
RSNA_LABELS = ("normal", "pneumonia", "other_abnormal")
RSNA_CLASSIFICATION_PROMPT = (
    "Classify this frontal chest radiograph. Reply with exactly one label: "
    "normal, pneumonia, or other_abnormal."
)
RSNA_LOCALIZATION_PROMPT = (
    "Analyze this frontal chest radiograph. Return only compact JSON with keys finding, boxes, impression. "
    "finding must be normal, pneumonia, or other_abnormal. boxes must contain normalized integer "
    "[x1,y1,x2,y2] coordinates from 0 to 1000 for pulmonary opacities, otherwise an empty list. "
    "No prose outside JSON."
)
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


def _find_numeric(value: Any, *keys: str) -> float | None:
    """Find the first numeric metric in a nested quality report."""
    if isinstance(value, dict):
        for key in keys:
            if key in value:
                try:
                    return float(value[key])
                except (TypeError, ValueError):
                    pass
        for nested in value.values():
            found = _find_numeric(nested, *keys)
            if found is not None:
                return found
    elif isinstance(value, list):
        for nested in value:
            found = _find_numeric(nested, *keys)
            if found is not None:
                return found
    return None


def _load_quality_state() -> dict[str, Any]:
    report_path = RSNA_V2_TEST_REPORT if RSNA_V2_TEST_REPORT.exists() else RSNA_V2_VALIDATION_REPORT
    state: dict[str, Any] = {
        "report_path": str(report_path) if report_path.exists() else None,
        "split": "test" if report_path == RSNA_V2_TEST_REPORT and report_path.exists() else "validation",
        "classification_gate_passed": False,
        "localization_gate_passed": False,
        "temperature": 1.0,
    }
    if not report_path.exists():
        return state
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception:
        return state

    macro_f1 = _find_numeric(report, "macro_f1", "macro-F1") or 0.0
    balanced_accuracy = _find_numeric(report, "balanced_accuracy", "balanced_acc") or 0.0
    pneumonia_sensitivity = _find_numeric(report, "pneumonia_sensitivity", "pneumonia_recall") or 0.0
    normal_recall = _find_numeric(report, "normal_recall") or 0.0
    mean_iou = _find_numeric(report, "mean_best_iou", "mean_iou", "mean_IoU") or 0.0
    hit_rate = _find_numeric(report, "hit_rate_iou_0_30", "hit_rate", "iou_0_30_hit_rate") or 0.0
    temperature = _find_numeric(report, "temperature") or 1.0

    classification_passed = (
        state["split"] == "test"
        and macro_f1 >= 0.65
        and balanced_accuracy >= 0.68
        and pneumonia_sensitivity >= 0.80
        and normal_recall >= 0.80
    )
    detector_report: dict[str, Any] = {}
    if RSNA_DETECTOR_REPORT.exists():
        try:
            detector_report = json.loads(RSNA_DETECTOR_REPORT.read_text(encoding="utf-8"))
        except Exception:
            detector_report = {}
    detector_metrics = detector_report.get("test_metrics") if isinstance(detector_report.get("test_metrics"), dict) else {}
    detector_mean_iou = float(detector_metrics.get("mean_best_iou") or 0.0)
    detector_hit_rate = float(detector_metrics.get("hit_rate_iou_0_30") or 0.0)
    localization_passed = (
        detector_report.get("split") == "test"
        and detector_report.get("patient_separated") is True
        and detector_mean_iou >= 0.20
        and detector_hit_rate >= 0.25
        and RSNA_DETECTOR_CHECKPOINT.exists()
    )
    state.update(
        classification_gate_passed=classification_passed,
        localization_gate_passed=localization_passed,
        localization_report_path=str(RSNA_DETECTOR_REPORT) if RSNA_DETECTOR_REPORT.exists() else None,
        localization_threshold=float(detector_report.get("validation_selected_threshold") or 0.35),
        localization_source=str(detector_report.get("detector_version") or "medai-rsna-frcnn-v1"),
        temperature=max(0.2, min(5.0, temperature)),
        metrics={
            "macro_f1": macro_f1,
            "balanced_accuracy": balanced_accuracy,
            "pneumonia_sensitivity": pneumonia_sensitivity,
            "normal_recall": normal_recall,
            "legacy_generative_mean_iou": mean_iou,
            "legacy_generative_hit_rate": hit_rate,
            "mean_iou": detector_mean_iou,
            "hit_rate": detector_hit_rate,
        },
    )
    return state

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
    "adapter_available": {name: False for name in ADAPTER_PATHS},
    "device": None,
    "quality": {},
    "detector": None,
    "detector_device": None,
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


def _prompt_inputs(processor: Any, image: Image.Image, prompt: str) -> dict[str, Any]:
    messages = [{
        "role": "user",
        "content": [
            {"type": "image", "image": image},
            {"type": "text", "text": prompt},
        ],
    }]
    rendered = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = processor(text=rendered, images=image, return_tensors="pt")
    device = _model_device(_runtime["model"])
    return {key: value.to(device) if hasattr(value, "to") else value for key, value in inputs.items()}


def _score_rsna_classification(model: Any, processor: Any, image: Image.Image) -> tuple[str, dict[str, float]]:
    base = _prompt_inputs(processor, image, RSNA_CLASSIFICATION_PROMPT)
    prefix_len = int(base["input_ids"].shape[1])
    tokenizer = processor.tokenizer
    scores: list[float] = []
    for label in RSNA_LABELS:
        answer = tokenizer(label, add_special_tokens=False, return_tensors="pt").input_ids
        answer = answer.to(base["input_ids"].device)
        input_ids = torch.cat([base["input_ids"], answer], dim=1)
        attention_mask = torch.cat([base["attention_mask"], torch.ones_like(answer)], dim=1)
        extra = {key: value for key, value in base.items() if key not in {"input_ids", "attention_mask"}}
        output = model(input_ids=input_ids, attention_mask=attention_mask, use_cache=False, **extra)
        logits = output.logits[:, prefix_len - 1: prefix_len - 1 + answer.shape[1], :].float()
        token_log_probability = torch.log_softmax(logits, dim=-1).gather(-1, answer.unsqueeze(-1)).squeeze(-1)
        scores.append(float(token_log_probability.sum().item() / max(1, answer.shape[1])))
        del output, logits, token_log_probability, input_ids, attention_mask

    temperature = float(_runtime.get("quality", {}).get("temperature") or 1.0)
    probabilities_tensor = torch.softmax(torch.tensor(scores, dtype=torch.float32) / temperature, dim=0)
    probabilities = {label: round(float(probabilities_tensor[index]), 6) for index, label in enumerate(RSNA_LABELS)}
    finding = max(probabilities, key=probabilities.get)
    return finding, probabilities


def _parse_localization_boxes(text: str) -> list[list[float]]:
    obj = _extract_json_object(text)
    if not isinstance(obj, dict):
        return []
    normalized: list[list[float]] = []
    boxes = obj.get("boxes")
    if not isinstance(boxes, list):
        return []
    for box in boxes:
        if not isinstance(box, list) or len(box) != 4:
            continue
        try:
            values = [max(0.0, min(1.0, float(value) / 1000.0)) for value in box]
        except (TypeError, ValueError):
            continue
        x1, y1, x2, y2 = values
        if x1 < x2 and y1 < y2:
            normalized.append(values)
    return normalized


def _generate_rsna_localization(model: Any, processor: Any, image: Image.Image) -> list[list[float]]:
    inputs = _prompt_inputs(processor, image, RSNA_LOCALIZATION_PROMPT)
    prompt_len = int(inputs["input_ids"].shape[1])
    generated = model.generate(
        **inputs,
        max_new_tokens=128,
        do_sample=False,
        num_beams=1,
        use_cache=True,
        repetition_penalty=1.05,
    )
    text = processor.tokenizer.decode(generated[0, prompt_len:], skip_special_tokens=True).strip()
    return _parse_localization_boxes(text)


def _detect_rsna_localization(image: Image.Image) -> list[list[float]]:
    """Return normalized boxes from the independently test-gated detector."""
    detector = _runtime.get("detector")
    device = _runtime.get("detector_device")
    quality = _runtime.get("quality", {})
    if detector is None or device is None or not quality.get("localization_gate_passed"):
        return []
    from torchvision.transforms.functional import pil_to_tensor

    width, height = image.size
    tensor = pil_to_tensor(image.convert("RGB")).float().div_(255.0).to(device)
    output = detector([tensor])[0]
    threshold = float(quality.get("localization_threshold") or 0.35)
    boxes: list[list[float]] = []
    for box, score in zip(output["boxes"].detach().cpu(), output["scores"].detach().cpu()):
        if float(score) < threshold:
            continue
        x1, y1, x2, y2 = (float(value) for value in box.tolist())
        normalized = [
            max(0.0, min(1.0, x1 / max(1, width))),
            max(0.0, min(1.0, y1 / max(1, height))),
            max(0.0, min(1.0, x2 / max(1, width))),
            max(0.0, min(1.0, y2 / max(1, height))),
        ]
        if normalized[0] < normalized[2] and normalized[1] < normalized[3]:
            boxes.append(normalized)
    return boxes


def _rsna_response(model: Any, processor: Any, image: Image.Image) -> dict[str, Any]:
    quality = _runtime.get("quality", {})
    with _generation_lock:
        adapter_context = _select_adapter(model, "rsna_v2")
        with adapter_context, torch.inference_mode():
            finding, probabilities = _score_rsna_classification(model, processor, image)
            boxes = _detect_rsna_localization(image) if finding == "pneumonia" else []

    confidence = probabilities[finding]
    localization_validated = bool(quality.get("localization_gate_passed")) and bool(boxes)
    localization_reason = None
    if not localization_validated:
        localization_reason = (
            "normal_study" if finding == "normal"
            else "no_localizable_pneumonia" if finding == "other_abnormal"
            else "localization_quality_gate_not_passed"
        )
    impression = {
        "normal": "Рентгенологических признаков острой кардиопульмональной патологии не выявлено.",
        "pneumonia": "Рентгенологические признаки очагово-инфильтративных изменений, соответствующих пневмонии.",
        "other_abnormal": "Выявлены патологические изменения, не классифицируемые как пневмония; требуется описание рентгенологом.",
    }[finding]
    evidence = []
    if localization_validated:
        evidence.append("Локализуемая область легочного затемнения отмечена на изображении.")
    result = {
        "finding": finding,
        "confidence": round(confidence, 6),
        "probabilities": probabilities,
        "impression": impression,
        "evidence": evidence,
        "bbox": boxes[0] if localization_validated else None,
        "localization": {
            "validated": localization_validated,
            "source": quality.get("localization_source") if localization_validated else None,
            "bbox": boxes[0] if localization_validated else None,
            "boxes": boxes if localization_validated else [],
            "reason": localization_reason,
        },
        "quality_gate_passed": bool(quality.get("classification_gate_passed")),
        "quality_report": quality.get("report_path"),
    }
    return {
        "text": json.dumps(result, ensure_ascii=False, separators=(",", ":")),
        "model_variant": "rsna_v2",
        "model_version": MODEL_LABELS["rsna_v2"],
    }


def _select_adapter(model: Any, model_variant: str):
    if model_variant == "base":
        disable = getattr(model, "disable_adapter", None)
        return disable() if callable(disable) else nullcontext()
    if model_variant not in ADAPTER_PATHS:
        raise HTTPException(status_code=422, detail="Unknown model_variant")
    if not _runtime["adapter_available"].get(model_variant, False):
        raise HTTPException(status_code=503, detail="Fine-tuned model is unavailable")
    set_adapter = getattr(model, "set_adapter", None)
    if callable(set_adapter):
        set_adapter(model_variant)
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
        "adapter_available": dict(_runtime["adapter_available"]),
        "quality": dict(_runtime.get("quality", {})),
        "model_variants": [
            {
                "id": "rsna_v2",
                "label": MODEL_LABELS["rsna_v2"],
                "available": bool(_runtime["adapter_available"].get("rsna_v2")),
                "quality_gate_passed": bool(_runtime.get("quality", {}).get("classification_gate_passed")),
                "localization_gate_passed": bool(_runtime.get("quality", {}).get("localization_gate_passed")),
            },
            {"id": "pneumonia_v1", "label": MODEL_LABELS["pneumonia_v1"], "available": bool(_runtime["adapter_available"].get("pneumonia_v1"))},
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
    if str(model_variant) == "rsna_v2":
        return _rsna_response(model, processor, image)

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


def configure_runtime(
    model: Any,
    processor: Any,
    adapter_available: bool | dict[str, bool],
    quality: dict[str, Any] | None = None,
    detector: Any = None,
    detector_device: torch.device | None = None,
) -> None:
    model.eval()
    if isinstance(adapter_available, bool):
        availability = {name: adapter_available if name == "pneumonia_v1" else False for name in ADAPTER_PATHS}
    else:
        availability = {name: bool(adapter_available.get(name)) for name in ADAPTER_PATHS}
    _runtime.update(
        model=model,
        processor=processor,
        adapter_available=availability,
        device=_model_device(model),
        quality=quality or _load_quality_state(),
        detector=detector,
        detector_device=detector_device,
    )


def start_api(
    model: Any,
    processor: Any,
    adapter_available: bool | dict[str, bool],
    detector: Any = None,
    detector_device: torch.device | None = None,
    host: str = "0.0.0.0",
    port: int = 8005,
):
    configure_runtime(model, processor, adapter_available, detector=detector, detector_device=detector_device)
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
    adapter_paths: dict[str, str | Path] | None = None,
    host: str = "0.0.0.0",
    port: int = 8005,
    local_files_only: bool = True,
):
    from peft import PeftModel
    from transformers import AutoModelForImageTextToText, AutoProcessor

    configured_paths = dict(ADAPTER_PATHS)
    configured_paths["pneumonia_v1"] = Path(adapter_path)
    if adapter_paths:
        configured_paths.update({name: Path(path) for name, path in adapter_paths.items()})
    available_paths = {
        name: Path(path)
        for name, path in configured_paths.items()
        if (Path(path) / "adapter_model.safetensors").exists()
    }

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
    model: Any = base_model
    for index, (name, path) in enumerate(available_paths.items()):
        if index == 0:
            model = PeftModel.from_pretrained(
                base_model,
                path,
                adapter_name=name,
                is_trainable=False,
            )
        else:
            model.load_adapter(path, adapter_name=name, is_trainable=False)
    detector = None
    detector_device = None
    quality = _load_quality_state()
    if quality.get("localization_gate_passed") and RSNA_DETECTOR_CHECKPOINT.exists():
        from torchvision.models.detection import fasterrcnn_resnet50_fpn_v2
        from torchvision.models.detection.faster_rcnn import FastRCNNPredictor

        detector = fasterrcnn_resnet50_fpn_v2(
            weights=None,
            min_size=640,
            max_size=1024,
            box_score_thresh=0.05,
            box_nms_thresh=0.35,
            box_detections_per_img=10,
        )
        in_features = detector.roi_heads.box_predictor.cls_score.in_features
        detector.roi_heads.box_predictor = FastRCNNPredictor(in_features, 2)
        checkpoint = torch.load(RSNA_DETECTOR_CHECKPOINT, map_location="cpu", weights_only=False)
        detector.load_state_dict(checkpoint["model"] if isinstance(checkpoint, dict) and "model" in checkpoint else checkpoint)
        detector_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        detector.to(detector_device).eval()
    thread = start_api(
        model,
        processor,
        adapter_available={name: name in available_paths for name in ADAPTER_PATHS},
        detector=detector,
        detector_device=detector_device,
        host=host,
        port=port,
    )
    return model, processor, thread


if __name__ == "__main__":
    loaded_model, loaded_processor, api_thread = load_and_start_api()
    api_thread.join()
