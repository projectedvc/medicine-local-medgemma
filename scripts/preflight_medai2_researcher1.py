"""Fail fast unless the isolated researcher1 two-GPU environment is healthy."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path

import torch


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--seed-adapter", type=Path, required=True)
    parser.add_argument("--minimum-free-gb", type=int, default=200)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    errors: list[str] = []
    gpu_count = torch.cuda.device_count() if torch.cuda.is_available() else 0
    gpu_rows: list[dict[str, object]] = []
    for index in range(gpu_count):
        properties = torch.cuda.get_device_properties(index)
        try:
            left = torch.ones((512, 512), device=f"cuda:{index}", dtype=torch.bfloat16)
            right = torch.ones((512, 512), device=f"cuda:{index}", dtype=torch.bfloat16)
            value = float((left @ right)[0, 0].item())
            smoke_ok = value == 512.0
        except Exception as exc:  # pragma: no cover - depends on GPU runtime
            smoke_ok = False
            errors.append(f"GPU {index} tensor smoke failed: {exc}")
        gpu_rows.append(
            {
                "index": index,
                "name": torch.cuda.get_device_name(index),
                "memory_gb": round(properties.total_memory / 1024**3, 2),
                "bf16_supported": torch.cuda.is_bf16_supported(),
                "tensor_smoke": smoke_ok,
            }
        )

    if gpu_count != 2:
        errors.append(f"researcher1 requires exactly 2 visible GPUs; found {gpu_count}")
    if gpu_count and not all(bool(row["bf16_supported"]) for row in gpu_rows):
        errors.append("all GPUs must support BF16")
    if not args.seed_adapter.joinpath("adapter_config.json").is_file():
        errors.append("seed adapter_config.json is missing")
    if not args.seed_adapter.joinpath("adapter_model.safetensors").is_file():
        errors.append("seed adapter_model.safetensors is missing")
    free_gb = shutil.disk_usage(args.workspace).free / 1024**3
    if free_gb < args.minimum_free_gb:
        errors.append(f"free disk {free_gb:.1f} GiB is below {args.minimum_free_gb} GiB")

    report = {
        "passed": not errors,
        "account_topology": {
            "student1": "single GPU production environment; do not modify",
            "student2": "single GPU independent environment; do not modify",
            "researcher1": "combined two-GPU MedAI 2.0 environment",
        },
        "cuda_available": torch.cuda.is_available(),
        "cuda_visible_devices": os.getenv("CUDA_VISIBLE_DEVICES"),
        "nvidia_visible_devices": os.getenv("NVIDIA_VISIBLE_DEVICES"),
        "gpu_count": gpu_count,
        "gpus": gpu_rows,
        "disk_free_gb": round(free_gb, 2),
        "seed_adapter": str(args.seed_adapter.resolve()),
        "errors": errors,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["passed"] else 2)


if __name__ == "__main__":
    main()
