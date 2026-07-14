# MedAI model training and release policy

This project uses staged adapters. Do not continue training one adapter across unrelated anatomy.

## Current chest sequence

1. `cxr_pneumonia_v2`: NORMAL vs PNEUMONIA.
2. A separate pneumothorax adapter/dataset after the binary adapter passes its gate.
3. Further chest findings as separate, versioned tasks.
4. Bone/fracture work starts as a separate anatomy family, manifest, adapter, and release gate.

The current `medai-pneumonia-v1` adapter is **not released**. A balanced 12-image smoke check produced only 2 usable correct answers. The UI may expose it for controlled comparison, but the backend must withhold its diagnostic class.

## Non-negotiable data rules

- Train only on manifest records with `split=train`.
- Tune hyperparameters on `split=validation`; use `split=test` once for the release gate.
- Split by patient before augmentation and deduplication to prevent leakage.
- Balance NORMAL and PNEUMONIA batches or deterministically downsample the majority class.
- Keep one production JSON schema: `finding`, `confidence`, `impression`, `evidence`.
- Mask prompt/image tokens in labels; loss is computed on the assistant answer only.
- Preserve the vision encoder for the first corrected BF16 LoRA run.
- Save adapters and quality reports under a new versioned directory; never overwrite a released artifact.

## Localization

The Kaggle pneumonia dataset has image-level class labels only. It cannot supervise lesion boxes, masks, or trustworthy heatmaps. Never display a generated box from this adapter.

Localization requires a separate dataset with expert boxes/masks and a separately validated detector or segmentation model. The production API exposes a region only when it arrives as:

```json
{
  "localization": {
    "validated": true,
    "source": "validated_detector_version",
    "bbox": [0.1, 0.2, 0.6, 0.7]
  }
}
```

Coordinates are normalized to the source image. Until that pipeline exists, return `localization.validated=false` and show an explicit “localization unavailable” message.

## Corrected training and release gate

Run training on the Jupyter GPU server, not on a workstation:

```bash
python scripts/finetune_medgemma_lora.py \
  --model google/medgemma-1.5-4b-it \
  --train-jsonl /home/jovyan/work/medgemma_finetune/manifests/cxr_pneumonia_binary_v1.jsonl \
  --output-dir /home/jovyan/work/medgemma_finetune/runs/cxr_pneumonia_v2/bf16_lora_balanced
```

After starting the GPU API with the new adapter, run at least 50 held-out images per class:

```bash
python scripts/evaluate_pneumonia_adapter.py \
  --manifest /home/jovyan/work/medgemma_finetune/manifests/cxr_pneumonia_binary_v1.jsonl \
  --endpoint http://127.0.0.1:8005 \
  --per-class 50 \
  --output /home/jovyan/work/medgemma_finetune/runs/cxr_pneumonia_v2/quality_gate.json
```

Release only when `passed=true`. These thresholds are engineering gates, not clinical validation or regulatory approval.
