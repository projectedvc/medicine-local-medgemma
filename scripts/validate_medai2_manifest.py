"""Validate a MedAI 2.0 multi-anatomy JSONL manifest before GPU training."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ALLOWED_SPLITS = {"train", "validation", "test"}
REQUIRED_FIELDS = {"image", "patient_id", "split", "anatomy", "task", "answer"}


def _answer(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, dict):
        raise ValueError("answer must be an object or a JSON object string")
    return value


def validate_manifest(
    manifest_path: Path,
    image_root: Path | None = None,
    require_test: bool = False,
) -> dict[str, Any]:
    raw = manifest_path.read_bytes()
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    split_patients: dict[str, set[str]] = defaultdict(set)
    split_images: dict[str, set[str]] = defaultdict(set)
    distribution: Counter[tuple[str, str, str, str]] = Counter()

    for line_number, line in enumerate(raw.decode("utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {line_number}: invalid JSON: {exc}")
            continue
        if not isinstance(row, dict):
            errors.append(f"line {line_number}: record must be an object")
            continue
        missing = sorted(REQUIRED_FIELDS - row.keys())
        if missing:
            errors.append(f"line {line_number}: missing fields: {', '.join(missing)}")
            continue

        split = str(row["split"]).strip().casefold()
        patient_id = str(row["patient_id"]).strip()
        image = str(row["image"]).strip()
        anatomy = str(row["anatomy"]).strip().casefold()
        task = str(row["task"]).strip().casefold()
        if split not in ALLOWED_SPLITS:
            errors.append(f"line {line_number}: unsupported split {split!r}")
        if not patient_id or not image or not anatomy or not task:
            errors.append(f"line {line_number}: identifiers, anatomy and task must be non-empty")
        try:
            answer = _answer(row["answer"])
        except (ValueError, json.JSONDecodeError) as exc:
            errors.append(f"line {line_number}: {exc}")
            continue
        finding = str(answer.get("finding") or "").strip().casefold()
        impression = str(answer.get("impression") or "").strip()
        evidence = answer.get("evidence")
        if not finding or not impression or not isinstance(evidence, list):
            errors.append(
                f"line {line_number}: answer requires finding, impression and an evidence list"
            )
        if "confidence" in answer:
            errors.append(
                f"line {line_number}: do not train self-reported confidence; calibrate it during evaluation"
            )
        if image_root is not None:
            image_path = Path(image)
            if not image_path.is_absolute():
                image_path = image_root / image_path
            if not image_path.is_file():
                errors.append(f"line {line_number}: image not found: {image_path}")

        split_patients[split].add(patient_id)
        split_images[split].add(image)
        distribution[(split, anatomy, task, finding)] += 1
        records.append(row)

    for left, right in (("train", "validation"), ("train", "test"), ("validation", "test")):
        leaked_patients = split_patients[left] & split_patients[right]
        leaked_images = split_images[left] & split_images[right]
        if leaked_patients:
            errors.append(f"patient leakage {left}/{right}: {len(leaked_patients)}")
        if leaked_images:
            errors.append(f"image leakage {left}/{right}: {len(leaked_images)}")

    present_splits = {str(row.get("split", "")).strip().casefold() for row in records}
    if "train" not in present_splits or "validation" not in present_splits:
        errors.append("manifest must contain train and validation splits")
    if require_test and "test" not in present_splits:
        errors.append("release manifest must contain an untouched test split")

    report = {
        "passed": not errors,
        "manifest": str(manifest_path.resolve()),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "records": len(records),
        "splits": {split: sum(1 for row in records if str(row["split"]).casefold() == split) for split in sorted(ALLOWED_SPLITS)},
        "patients": {split: len(values) for split, values in sorted(split_patients.items())},
        "distribution": [
            {"split": key[0], "anatomy": key[1], "task": key[2], "finding": key[3], "count": count}
            for key, count in sorted(distribution.items())
        ],
        "errors": errors,
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--image-root", type=Path)
    parser.add_argument("--require-test", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = validate_manifest(args.manifest, args.image_root, args.require_test)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    raise SystemExit(0 if report["passed"] else 2)


if __name__ == "__main__":
    main()
