import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F
from PIL import Image
from peft import LoraConfig, get_peft_model
from torch.utils.data import Dataset
from transformers import AutoModelForImageTextToText, AutoProcessor, Trainer, TrainingArguments


PROMPT = """Внимательно оцените саму рентгенограмму грудной клетки.
Выберите один класс: normal, pneumonia или not_diagnostic. Верните только JSON с полями
finding, confidence, impression и evidence. impression — краткое фактическое заключение на
русском по этому пациенту, evidence — только реально видимые признаки. Не возвращайте
координаты: этот набор данных не содержит разметки очагов."""


def _read_records(path: Path, split: str) -> list[dict[str, Any]]:
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    selected = [row for row in records if str(row.get("split", "train")).casefold() == split.casefold()]
    if split == "validation" and not selected:
        selected = [row for row in records if str(row.get("split", "")).casefold() == "val"]
    return selected


def _label(row: dict[str, Any]) -> str:
    answer = row.get("answer")
    if isinstance(answer, str):
        try:
            answer = json.loads(answer)
        except json.JSONDecodeError:
            answer = {}
    answer = answer if isinstance(answer, dict) else {}
    return str(row.get("label") or answer.get("finding") or answer.get("classification") or "").upper()


def _balanced(records: list[dict[str, Any]], seed: int) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        grouped[_label(row)].append(row)
    non_empty = [rows for label, rows in grouped.items() if label and rows]
    if len(non_empty) < 2:
        raise ValueError("Balanced training requires at least two non-empty classes")
    target = min(len(rows) for rows in non_empty)
    rng = random.Random(seed)
    result = [row for rows in non_empty for row in rng.sample(rows, target)]
    rng.shuffle(result)
    return result


def _normalized_answer(row: dict[str, Any]) -> str:
    answer = row.get("answer")
    if isinstance(answer, str):
        try:
            answer = json.loads(answer)
        except json.JSONDecodeError:
            answer = {"impression": answer}
    answer = answer if isinstance(answer, dict) else {}
    finding = str(answer.get("finding") or answer.get("classification") or row.get("label") or "not_diagnostic")
    finding = finding.strip().casefold().replace(" ", "_")
    if finding not in {"normal", "pneumonia"}:
        finding = "not_diagnostic"
    evidence = answer.get("evidence") or answer.get("findings") or []
    if isinstance(evidence, str):
        evidence = [evidence]
    evidence = [str(item).strip() for item in evidence[:3] if str(item).strip()]
    impression = str(answer.get("impression") or "").strip()
    if not impression:
        impression = "Острой патологии не выявлено." if finding == "normal" else "Рентгенологические признаки пневмонии."
    return json.dumps(
        {
            "finding": finding,
            "confidence": answer.get("confidence", 0.9),
            "impression": impression,
            "evidence": evidence,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


class JsonlImageReportDataset(Dataset):
    def __init__(self, records: list[dict[str, Any]], image_root: Path, processor: Any):
        self.records = records
        self.image_root = image_root
        self.processor = processor

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        row = self.records[index]
        image_path = Path(row["image"])
        if not image_path.is_absolute():
            image_path = self.image_root / image_path
        image = Image.open(image_path).convert("RGB")
        # Use the exact production schema; legacy manifest prompts used different
        # field names and were a direct source of invalid inference responses.
        clinical_note = str(row.get("clinical_note") or "").strip()
        prompt = PROMPT if not clinical_note else f"{PROMPT}\nКлиническая заметка: {clinical_note}"
        user_message = {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": prompt},
            ],
        }
        full_messages = [
            user_message,
            {"role": "assistant", "content": [{"type": "text", "text": _normalized_answer(row)}]},
        ]
        encoded = self.processor.apply_chat_template(
            full_messages,
            add_generation_prompt=False,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        )
        prompt_encoded = self.processor.apply_chat_template(
            [user_message],
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
    padded: dict[str, torch.Tensor] = {}
    for key in ("input_ids", "attention_mask", "token_type_ids", "labels"):
        if key not in batch[0]:
            continue
        pad_value = -100 if key == "labels" else (processor.tokenizer.pad_token_id if key == "input_ids" else 0)
        padded[key] = torch.stack(
            [F.pad(item[key], (0, max_length - item[key].shape[-1]), value=pad_value) for item in batch]
        )
    for key in batch[0]:
        if key not in padded and key != "labels":
            padded[key] = torch.stack([item[key] for item in batch])
    return padded


def main() -> None:
    parser = argparse.ArgumentParser(description="Balanced BF16 LoRA training for MedAI chest classification.")
    parser.add_argument("--model", default="google/medgemma-1.5-4b-it")
    parser.add_argument("--train-jsonl", required=True)
    parser.add_argument("--image-root", default=".")
    parser.add_argument("--output-dir", default="../adapters/medgemma-lora")
    parser.add_argument("--epochs", type=float, default=1.0)
    parser.add_argument("--learning-rate", type=float, default=1e-5)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-balance-classes", action="store_true")
    args = parser.parse_args()

    manifest_path = Path(args.train_jsonl)
    train_records = _read_records(manifest_path, "train")
    validation_records = _read_records(manifest_path, "validation")
    if not train_records:
        raise ValueError("The manifest has no records with split=train")
    if not args.no_balance_classes:
        train_records = _balanced(train_records, args.seed)
    print("train classes:", dict(Counter(_label(row) for row in train_records)))
    print("validation classes:", dict(Counter(_label(row) for row in validation_records)))

    processor = AutoProcessor.from_pretrained(args.model)
    model = AutoModelForImageTextToText.from_pretrained(
        args.model,
        torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
        device_map="auto" if torch.cuda.is_available() else None,
    )
    model.gradient_checkpointing_enable()
    model.config.use_cache = False
    model = get_peft_model(
        model,
        LoraConfig(
            r=8,
            lora_alpha=16,
            lora_dropout=0.05,
            bias="none",
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
            task_type="CAUSAL_LM",
        ),
    )
    # Preserve the visual encoder; this run adapts only language projections.
    for name, parameter in model.named_parameters():
        if "vision" in name.casefold() or "visual" in name.casefold():
            parameter.requires_grad = False
    model.print_trainable_parameters()

    train_dataset = JsonlImageReportDataset(train_records, Path(args.image_root), processor)
    eval_dataset = JsonlImageReportDataset(validation_records, Path(args.image_root), processor) if validation_records else None
    trainer = Trainer(
        model=model,
        args=TrainingArguments(
            output_dir=args.output_dir,
            num_train_epochs=args.epochs,
            learning_rate=args.learning_rate,
            per_device_train_batch_size=args.batch_size,
            per_device_eval_batch_size=args.batch_size,
            gradient_accumulation_steps=args.gradient_accumulation_steps,
            logging_steps=5,
            save_strategy="epoch",
            eval_strategy="epoch" if eval_dataset else "no",
            load_best_model_at_end=bool(eval_dataset),
            metric_for_best_model="eval_loss" if eval_dataset else None,
            greater_is_better=False if eval_dataset else None,
            remove_unused_columns=False,
            bf16=torch.cuda.is_available(),
            seed=args.seed,
            data_seed=args.seed,
            report_to="none",
        ),
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=lambda batch: collate(batch, processor),
    )
    trainer.train()
    model.save_pretrained(args.output_dir)
    processor.save_pretrained(args.output_dir)


if __name__ == "__main__":
    main()
