"""Full-parameter MedGemma 1.5 training for the isolated researcher1 profile.

Launch only through the checked-in two-GPU Accelerate/FSDP2 configuration. The
MedAI 1.0 adapter is merged into a new in-memory candidate and is never edited.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F
from peft import PeftModel
from PIL import Image
from torch.utils.data import Dataset
from transformers import AutoModelForImageTextToText, AutoProcessor, Trainer, TrainingArguments

from validate_medai2_manifest import validate_manifest


def _load_rows(path: Path, split: str) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [row for row in rows if str(row["split"]).casefold() == split]


def _answer_text(row: dict[str, Any]) -> str:
    answer = row["answer"]
    if isinstance(answer, str):
        answer = json.loads(answer)
    clean = {
        "finding": str(answer["finding"]).strip().casefold().replace(" ", "_"),
        "impression": str(answer["impression"]).strip(),
        "evidence": [str(value).strip() for value in answer["evidence"] if str(value).strip()][:5],
    }
    return json.dumps(clean, ensure_ascii=False, separators=(",", ":"))


class MedAI2Dataset(Dataset):
    def __init__(self, rows: list[dict[str, Any]], image_root: Path, processor: Any):
        self.rows = rows
        self.image_root = image_root
        self.processor = processor

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        row = self.rows[index]
        image_path = Path(row["image"])
        if not image_path.is_absolute():
            image_path = self.image_root / image_path
        image = Image.open(image_path).convert("RGB")
        prompt = str(row.get("prompt") or "").strip()
        if not prompt:
            prompt = (
                f"Review this {row['anatomy']} study for task {row['task']}. "
                "Return only JSON with finding, impression and evidence. "
                "Do not invent coordinates or confidence."
            )
        user = {
            "role": "user",
            "content": [{"type": "image", "image": image}, {"type": "text", "text": prompt}],
        }
        conversation = [
            user,
            {"role": "assistant", "content": [{"type": "text", "text": _answer_text(row)}]},
        ]
        encoded = self.processor.apply_chat_template(
            conversation,
            add_generation_prompt=False,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        )
        prompt_encoded = self.processor.apply_chat_template(
            [user],
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        )
        item = {key: value.squeeze(0) for key, value in encoded.items()}
        labels = item["input_ids"].clone()
        prompt_length = min(prompt_encoded["input_ids"].shape[-1], labels.shape[-1])
        labels[:prompt_length] = -100
        item["labels"] = labels
        return item


def collate(batch: list[dict[str, torch.Tensor]], processor: Any) -> dict[str, torch.Tensor]:
    max_length = max(item["input_ids"].shape[-1] for item in batch)
    result: dict[str, torch.Tensor] = {}
    for key in batch[0]:
        values = [item[key] for item in batch]
        if key in {"input_ids", "attention_mask", "token_type_ids", "labels"}:
            pad_value = -100 if key == "labels" else (processor.tokenizer.pad_token_id if key == "input_ids" else 0)
            result[key] = torch.stack(
                [F.pad(value, (0, max_length - value.shape[-1]), value=pad_value) for value in values]
            )
        else:
            result[key] = torch.stack(values)
    return result


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_head() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--image-root", type=Path, required=True)
    parser.add_argument("--seed-adapter", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--resume-from-checkpoint")
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()

    world_size = int(os.getenv("WORLD_SIZE", "1"))
    if world_size != 2:
        raise RuntimeError(f"MedAI 2.0 full training requires WORLD_SIZE=2; found {world_size}")
    if not torch.cuda.is_available() or torch.cuda.device_count() != 2:
        raise RuntimeError("researcher1 must expose two working CUDA GPUs")

    manifest_report = validate_manifest(args.manifest, args.image_root, require_test=True)
    if not manifest_report["passed"]:
        raise ValueError("manifest validation failed: " + "; ".join(manifest_report["errors"]))
    config = json.loads(args.config.read_text(encoding="utf-8"))
    train_rows = _load_rows(args.manifest, "train")
    validation_rows = _load_rows(args.manifest, "validation")
    anatomy_counts = Counter(str(row["anatomy"]).casefold() for row in train_rows)
    if len(anatomy_counts) < 2 and not args.smoke:
        raise ValueError("full MedAI 2.0 run requires at least two anatomy families")
    total = sum(anatomy_counts.values())
    chest_ratio = anatomy_counts.get("chest", 0) / max(total, 1)
    if chest_ratio < float(config["minimum_replay_ratio"]):
        raise ValueError("chest replay ratio is below the configured anti-forgetting floor")

    model_id = str(config.get("model", "google/medgemma-1.5-4b-it"))
    processor = AutoProcessor.from_pretrained(model_id)
    base_model = AutoModelForImageTextToText.from_pretrained(
        model_id,
        torch_dtype=torch.bfloat16,
        low_cpu_mem_usage=True,
        attn_implementation="sdpa",
    )
    seeded = PeftModel.from_pretrained(base_model, args.seed_adapter, is_trainable=False)
    model = seeded.merge_and_unload(safe_merge=True)
    model.config.use_cache = False
    for parameter in model.parameters():
        parameter.requires_grad = True

    train_dataset = MedAI2Dataset(train_rows, args.image_root, processor)
    eval_dataset = MedAI2Dataset(validation_rows, args.image_root, processor)
    training_args = TrainingArguments(
        output_dir=str(args.output_dir),
        num_train_epochs=float(config["epochs"]),
        max_steps=20 if args.smoke else -1,
        learning_rate=float(config["learning_rate"]),
        per_device_train_batch_size=int(config["per_device_train_batch_size"]),
        per_device_eval_batch_size=int(config["per_device_eval_batch_size"]),
        gradient_accumulation_steps=int(config["gradient_accumulation_steps"]),
        warmup_ratio=float(config["warmup_ratio"]),
        weight_decay=float(config["weight_decay"]),
        max_grad_norm=float(config["max_grad_norm"]),
        lr_scheduler_type="cosine",
        optim="adamw_torch_fused",
        bf16=True,
        tf32=True,
        logging_steps=int(config["logging_steps"]),
        eval_strategy="steps",
        eval_steps=10 if args.smoke else int(config["eval_steps"]),
        save_strategy="steps",
        save_steps=20 if args.smoke else int(config["save_steps"]),
        save_total_limit=int(config["save_total_limit"]),
        remove_unused_columns=False,
        dataloader_num_workers=4,
        dataloader_pin_memory=True,
        seed=int(config["seed"]),
        data_seed=int(config["seed"]),
        report_to="none",
        run_name="medai2-full-smoke" if args.smoke else "medai2-full",
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    if int(os.getenv("RANK", "0")) == 0:
        metadata = {
            "candidate": "MedAI 2.0",
            "base_model": model_id,
            "seed_adapter": str(args.seed_adapter.resolve()),
            "seed_adapter_sha256": _sha256(args.seed_adapter / "adapter_model.safetensors"),
            "manifest": manifest_report,
            "anatomy_counts": dict(anatomy_counts),
            "full_parameter_training": True,
            "world_size": world_size,
            "git_head": _git_head(),
            "python": platform.python_version(),
            "torch": torch.__version__,
            "smoke": args.smoke,
        }
        (args.output_dir / "run_metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=lambda rows: collate(rows, processor),
        processing_class=processor,
    )
    trainer.train(resume_from_checkpoint=args.resume_from_checkpoint)
    trainer.save_model(str(args.output_dir / "final_model"))
    processor.save_pretrained(args.output_dir / "final_model")


if __name__ == "__main__":
    main()
