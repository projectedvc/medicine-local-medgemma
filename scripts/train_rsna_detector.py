"""Train and independently validate the MedAI RSNA pneumonia box detector.

The classifier and localizer have separate quality gates.  This script uses the
patient-separated case manifests prepared by the RSNA v2 pipeline, tunes the
score threshold on validation only, and opens the untouched test split once for
the final report.
"""

from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path
from typing import Any

import torch
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from torchvision.models.detection import (
    FasterRCNN_ResNet50_FPN_V2_Weights,
    fasterrcnn_resnet50_fpn_v2,
)
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.transforms.functional import pil_to_tensor


def read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
                if limit and len(rows) >= limit:
                    break
    return rows


class RsnaDetectionDataset(Dataset):
    def __init__(self, manifest: Path, limit: int | None = None) -> None:
        self.rows = read_jsonl(manifest, limit)

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int):
        row = self.rows[index]
        image = Image.open(row["image_path"]).convert("RGB")
        tensor = pil_to_tensor(image).float().div_(255.0)
        width, height = image.size
        raw_boxes = row.get("boxes") or []
        boxes: list[list[float]] = []
        for value in raw_boxes:
            if not isinstance(value, list) or len(value) != 4:
                continue
            x1, y1, x2, y2 = (float(item) for item in value)
            x1, x2 = sorted((max(0.0, min(width - 1.0, x1)), max(1.0, min(float(width), x2))))
            y1, y2 = sorted((max(0.0, min(height - 1.0, y1)), max(1.0, min(float(height), y2))))
            if x2 - x1 >= 2 and y2 - y1 >= 2:
                boxes.append([x1, y1, x2, y2])
        box_tensor = torch.tensor(boxes, dtype=torch.float32).reshape(-1, 4)
        target = {
            "boxes": box_tensor,
            "labels": torch.ones((len(box_tensor),), dtype=torch.int64),
            "image_id": torch.tensor([index], dtype=torch.int64),
            "area": ((box_tensor[:, 2] - box_tensor[:, 0]) * (box_tensor[:, 3] - box_tensor[:, 1])) if len(box_tensor) else torch.zeros(0),
            "iscrowd": torch.zeros((len(box_tensor),), dtype=torch.int64),
        }
        return tensor, target, row


def collate(batch):
    images, targets, rows = zip(*batch)
    return list(images), list(targets), list(rows)


def make_model(pretrained: bool = True):
    weights = FasterRCNN_ResNet50_FPN_V2_Weights.DEFAULT if pretrained else None
    model = fasterrcnn_resnet50_fpn_v2(
        weights=weights,
        trainable_backbone_layers=3 if pretrained else None,
        min_size=640,
        max_size=1024,
        box_score_thresh=0.05,
        box_nms_thresh=0.35,
        box_detections_per_img=10,
    )
    in_features = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, 2)
    return model


def iou(box_a: list[float], box_b: list[float]) -> float:
    left = max(box_a[0], box_b[0])
    top = max(box_a[1], box_b[1])
    right = min(box_a[2], box_b[2])
    bottom = min(box_a[3], box_b[3])
    intersection = max(0.0, right - left) * max(0.0, bottom - top)
    area_a = max(0.0, box_a[2] - box_a[0]) * max(0.0, box_a[3] - box_a[1])
    area_b = max(0.0, box_b[2] - box_b[0]) * max(0.0, box_b[3] - box_b[1])
    return intersection / max(1e-8, area_a + area_b - intersection)


@torch.inference_mode()
def collect_predictions(model, loader, device: torch.device) -> list[dict[str, Any]]:
    model.eval()
    collected: list[dict[str, Any]] = []
    for images, targets, rows in loader:
        outputs = model([image.to(device, non_blocking=True) for image in images])
        for output, target, row in zip(outputs, targets, rows):
            predictions = [
                {"box": box.tolist(), "score": float(score)}
                for box, score in zip(output["boxes"].cpu(), output["scores"].cpu())
            ]
            collected.append({
                "case_id": row["case_id"],
                "patient_id": row["patient_id"],
                "label": row["label"],
                "ground_truth": target["boxes"].tolist(),
                "predictions": predictions,
            })
    return collected


def metrics_at_threshold(rows: list[dict[str, Any]], threshold: float) -> dict[str, float]:
    positive_count = 0
    negative_count = 0
    detected_positive = 0
    false_positive = 0
    best_ious: list[float] = []
    for row in rows:
        predictions = [item["box"] for item in row["predictions"] if item["score"] >= threshold]
        ground_truth = row["ground_truth"]
        if ground_truth:
            positive_count += 1
            if predictions:
                detected_positive += 1
            best = max((iou(pred, truth) for pred in predictions for truth in ground_truth), default=0.0)
            best_ious.append(best)
        else:
            negative_count += 1
            if predictions:
                false_positive += 1
    sensitivity = detected_positive / max(1, positive_count)
    false_positive_rate = false_positive / max(1, negative_count)
    precision = detected_positive / max(1, detected_positive + false_positive)
    f1 = 2 * precision * sensitivity / max(1e-8, precision + sensitivity)
    return {
        "threshold": threshold,
        "positive_cases": positive_count,
        "negative_cases": negative_count,
        "sensitivity": sensitivity,
        "precision": precision,
        "f1": f1,
        "false_positive_rate": false_positive_rate,
        "mean_best_iou": sum(best_ious) / max(1, len(best_ious)),
        "hit_rate_iou_0_30": sum(value >= 0.30 for value in best_ious) / max(1, len(best_ious)),
        "hit_rate_iou_0_50": sum(value >= 0.50 for value in best_ious) / max(1, len(best_ious)),
    }


def choose_validation_threshold(rows: list[dict[str, Any]]) -> dict[str, float]:
    candidates = [metrics_at_threshold(rows, value / 100) for value in range(15, 76, 5)]
    return max(candidates, key=lambda item: (item["f1"], item["mean_best_iou"], -item["false_positive_rate"]))


def patient_ids(path: Path) -> set[str]:
    return {str(row["patient_id"]) for row in read_jsonl(path)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", type=Path, default=Path("/home/jovyan/work/datasets/rsna_pneumonia_2018"))
    parser.add_argument("--output-dir", type=Path, default=Path("/home/jovyan/work/medgemma_rsna_v2/detector/rsna_frcnn_v1"))
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--limit-train", type=int)
    parser.add_argument("--limit-eval", type=int)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    if not torch.cuda.is_available():
        raise SystemExit("CUDA is required for detector training")
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    device = torch.device("cuda")
    manifests = args.dataset_root / "manifests"
    train_path = manifests / "train_balanced_cases.jsonl"
    validation_path = manifests / "validation_cases.jsonl"
    test_path = manifests / "test_cases.jsonl"
    split_ids = {"train": patient_ids(train_path), "validation": patient_ids(validation_path), "test": patient_ids(test_path)}
    if split_ids["train"] & split_ids["validation"] or split_ids["train"] & split_ids["test"] or split_ids["validation"] & split_ids["test"]:
        raise SystemExit("Patient leakage detected between RSNA splits")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    train_data = RsnaDetectionDataset(train_path, args.limit_train)
    validation_data = RsnaDetectionDataset(validation_path, args.limit_eval)
    test_data = RsnaDetectionDataset(test_path, args.limit_eval)
    loader_args = {"batch_size": args.batch_size, "num_workers": args.workers, "pin_memory": True, "collate_fn": collate}
    train_loader = DataLoader(train_data, shuffle=True, drop_last=True, **loader_args)
    validation_loader = DataLoader(validation_data, shuffle=False, **loader_args)
    test_loader = DataLoader(test_data, shuffle=False, **loader_args)

    model = make_model(pretrained=True).to(device)
    optimizer = torch.optim.AdamW((parameter for parameter in model.parameters() if parameter.requires_grad), lr=args.learning_rate, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(1, args.epochs))
    checkpoint_path = args.output_dir / "detector.pt"
    start_epoch = 0
    best_score = -1.0
    if args.resume and checkpoint_path.exists():
        checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
        model.load_state_dict(checkpoint["model"])
        optimizer.load_state_dict(checkpoint["optimizer"])
        start_epoch = int(checkpoint.get("epoch", -1)) + 1
        best_score = float(checkpoint.get("best_validation_score", -1.0))

    history: list[dict[str, Any]] = []
    for epoch in range(start_epoch, args.epochs):
        model.train()
        running_loss = 0.0
        started = time.time()
        for step, (images, targets, _) in enumerate(train_loader, start=1):
            images = [image.to(device, non_blocking=True) for image in images]
            targets = [{key: value.to(device, non_blocking=True) for key, value in target.items()} for target in targets]
            optimizer.zero_grad(set_to_none=True)
            with torch.amp.autocast("cuda", dtype=torch.bfloat16):
                losses = model(images, targets)
                loss = sum(losses.values())
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            optimizer.step()
            running_loss += float(loss.detach())
            if step % 100 == 0:
                print(json.dumps({"epoch": epoch + 1, "step": step, "steps": len(train_loader), "loss": running_loss / step, "vram_gb": torch.cuda.max_memory_allocated() / 2**30}), flush=True)
        scheduler.step()
        validation_rows = collect_predictions(model, validation_loader, device)
        validation_metrics = choose_validation_threshold(validation_rows)
        validation_score = validation_metrics["mean_best_iou"] + validation_metrics["hit_rate_iou_0_30"]
        epoch_record = {"epoch": epoch + 1, "train_loss": running_loss / max(1, len(train_loader)), "seconds": time.time() - started, "validation": validation_metrics}
        history.append(epoch_record)
        print(json.dumps(epoch_record), flush=True)
        if validation_score >= best_score:
            best_score = validation_score
            torch.save({"model": model.state_dict(), "optimizer": optimizer.state_dict(), "epoch": epoch, "best_validation_score": best_score}, checkpoint_path)
            (args.output_dir / "validation_predictions.json").write_text(json.dumps(validation_rows), encoding="utf-8")

    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    model.load_state_dict(checkpoint["model"])
    validation_rows = collect_predictions(model, validation_loader, device)
    selected = choose_validation_threshold(validation_rows)
    test_rows = collect_predictions(model, test_loader, device)
    test_metrics = metrics_at_threshold(test_rows, selected["threshold"])
    gate_passed = test_metrics["mean_best_iou"] >= 0.20 and test_metrics["hit_rate_iou_0_30"] >= 0.25
    report = {
        "schema_version": 1,
        "detector_version": "medai-rsna-frcnn-v1",
        "split": "test",
        "patient_separated": True,
        "train_patients": len(split_ids["train"]),
        "validation_patients": len(split_ids["validation"]),
        "test_patients": len(split_ids["test"]),
        "validation_selected_threshold": selected["threshold"],
        "validation_metrics": selected,
        "test_metrics": test_metrics,
        "localization_gate_passed": gate_passed,
        "gate": {"mean_best_iou": 0.20, "hit_rate_iou_0_30": 0.25},
        "checkpoint": str(checkpoint_path),
        "history": history,
    }
    (args.output_dir / "quality_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.output_dir / "test_predictions.json").write_text(json.dumps(test_rows), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
