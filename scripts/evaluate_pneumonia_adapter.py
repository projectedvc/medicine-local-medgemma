"""Balanced release gate for a pneumonia/normal adapter served by the GPU API."""

import argparse
import base64
import json
import random
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any


def _label(row: dict[str, Any]) -> str:
    return str(row.get("label") or "").strip().casefold()


def _read_balanced(path: Path, per_class: int, seed: int) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if str(row.get("split", "")).casefold() != "test":
            continue
        label = _label(row)
        if label in {"normal", "pneumonia"}:
            grouped[label].append(row)
    if not all(grouped[label] for label in ("normal", "pneumonia")):
        raise ValueError("The test split must contain both NORMAL and PNEUMONIA")
    count = min(per_class, len(grouped["normal"]), len(grouped["pneumonia"]))
    rng = random.Random(seed)
    rows = rng.sample(grouped["normal"], count) + rng.sample(grouped["pneumonia"], count)
    rng.shuffle(rows)
    return rows


def _predict(endpoint: str, row: dict[str, Any], model_variant: str) -> str:
    image = Path(row["image"])
    body = json.dumps(
        {
            "image_base64": base64.b64encode(image.read_bytes()).decode("ascii"),
            "model_variant": model_variant,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        endpoint.rstrip("/") + "/generate",
        data=body,
        headers={"Content-Type": "application/json", "ngrok-skip-browser-warning": "true"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        outer = json.loads(response.read().decode("utf-8"))
    payload = outer.get("text") or outer.get("response") or outer
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            return "invalid"
    finding = str(payload.get("finding") or payload.get("prediction") or "invalid").casefold()
    aliases = {"no finding": "normal", "no_finding": "normal"}
    finding = aliases.get(finding, finding.replace(" ", "_"))
    return finding if finding in {"normal", "pneumonia"} else "invalid"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the balanced MedAI release gate.")
    parser.add_argument("--endpoint", default="http://127.0.0.1:8005")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--model-variant", default="pneumonia_v1")
    parser.add_argument("--per-class", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default="quality_gate.json")
    args = parser.parse_args()

    rows = _read_balanced(Path(args.manifest), args.per_class, args.seed)
    confusion = {truth: {pred: 0 for pred in ("normal", "pneumonia", "invalid")} for truth in ("normal", "pneumonia")}
    samples: list[dict[str, str]] = []
    for index, row in enumerate(rows, 1):
        truth = _label(row)
        prediction = _predict(args.endpoint, row, args.model_variant)
        confusion[truth][prediction] += 1
        samples.append({"sample_id": str(row.get("sample_id", index)), "truth": truth, "prediction": prediction})
        print(f"[{index:03d}/{len(rows):03d}] {truth:9s} -> {prediction}")

    normal_total = sum(confusion["normal"].values())
    pneumonia_total = sum(confusion["pneumonia"].values())
    specificity = confusion["normal"]["normal"] / normal_total
    sensitivity = confusion["pneumonia"]["pneumonia"] / pneumonia_total
    balanced_accuracy = (specificity + sensitivity) / 2
    invalid_rate = sum(confusion[truth]["invalid"] for truth in confusion) / len(rows)
    passed = sensitivity >= 0.80 and specificity >= 0.80 and balanced_accuracy >= 0.82 and invalid_rate <= 0.05
    result = {
        "model_variant": args.model_variant,
        "samples": len(rows),
        "confusion": confusion,
        "sensitivity": round(sensitivity, 4),
        "specificity": round(specificity, 4),
        "balanced_accuracy": round(balanced_accuracy, 4),
        "invalid_rate": round(invalid_rate, 4),
        "thresholds": {"sensitivity": 0.80, "specificity": 0.80, "balanced_accuracy": 0.82, "invalid_rate_max": 0.05},
        "passed": passed,
        "sample_results": samples,
    }
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "sample_results"}, ensure_ascii=False, indent=2))
    if not passed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
