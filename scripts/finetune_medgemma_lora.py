import argparse
import json
from pathlib import Path
from typing import Any

import torch
from PIL import Image
from peft import LoraConfig, get_peft_model
from torch.utils.data import Dataset
from transformers import AutoModelForImageTextToText, AutoProcessor, Trainer, TrainingArguments


PROMPT = """
You are adapting MedGemMA for local radiology decision support.
Given the image and clinical context, produce the target report text.
This output is a draft for clinician review, not a final diagnosis.
""".strip()


class JsonlImageReportDataset(Dataset):
    def __init__(self, path: Path, image_root: Path, processor: Any):
        self.records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.image_root = image_root
        self.processor = processor

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        row = self.records[index]
        image_path = self.image_root / row["image"]
        image = Image.open(image_path).convert("RGB")
        clinical_note = row.get("clinical_note") or "not provided"
        answer = row["answer"]
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": f"{PROMPT}\nClinical note: {clinical_note}"},
                ],
            },
            {"role": "assistant", "content": [{"type": "text", "text": answer}]},
        ]
        encoded = self.processor.apply_chat_template(
            messages,
            add_generation_prompt=False,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        )
        item = {key: value.squeeze(0) for key, value in encoded.items()}
        item["labels"] = item["input_ids"].clone()
        return item


def collate(batch: list[dict[str, torch.Tensor]], processor: Any) -> dict[str, torch.Tensor]:
    return processor.tokenizer.pad(batch, return_tensors="pt")


def main() -> None:
    parser = argparse.ArgumentParser(description="LoRA fine-tuning scaffold for local MedGemMA.")
    parser.add_argument("--model", default="../models/medgemma-1.5-4b-it")
    parser.add_argument("--train-jsonl", required=True)
    parser.add_argument("--image-root", default=".")
    parser.add_argument("--output-dir", default="../adapters/medgemma-lora")
    parser.add_argument("--epochs", type=float, default=1.0)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=8)
    args = parser.parse_args()

    model_path = Path(args.model)
    processor = AutoProcessor.from_pretrained(model_path, local_files_only=True)
    model = AutoModelForImageTextToText.from_pretrained(
        model_path,
        torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
        device_map="auto" if torch.cuda.is_available() else None,
        local_files_only=True,
    )
    model.gradient_checkpointing_enable()
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

    train_dataset = JsonlImageReportDataset(Path(args.train_jsonl), Path(args.image_root), processor)
    trainer = Trainer(
        model=model,
        args=TrainingArguments(
            output_dir=args.output_dir,
            num_train_epochs=args.epochs,
            learning_rate=args.learning_rate,
            per_device_train_batch_size=args.batch_size,
            gradient_accumulation_steps=args.gradient_accumulation_steps,
            logging_steps=5,
            save_strategy="epoch",
            remove_unused_columns=False,
            bf16=torch.cuda.is_available(),
        ),
        train_dataset=train_dataset,
        data_collator=lambda batch: collate(batch, processor),
    )
    trainer.train()
    model.save_pretrained(args.output_dir)
    processor.save_pretrained(args.output_dir)


if __name__ == "__main__":
    main()
