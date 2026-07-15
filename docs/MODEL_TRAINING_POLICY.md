# MedAI model training and release policy

This project uses staged adapters. Do not continue training one adapter across unrelated anatomy.

## Current chest sequence

1. `medai-rsna-pneumonia-v2`: NORMAL vs PNEUMONIA vs OTHER_ABNORMAL, trained with patient-separated RSNA tasks.
2. A separate pneumothorax adapter/dataset after the binary adapter passes its gate.
3. Further chest findings as separate, versioned tasks.
4. Bone/fracture work starts as a separate anatomy family, manifest, adapter, and release gate.

The current `medai-pneumonia-v1` adapter is available as an **experimental testing model**. A small balanced smoke check produced only 2 usable correct answers out of 12, so the UI must show that limitation and require clinician review. The backend must still return its class and draft when the ordinary confidence threshold is met; do not silently withhold a model the user explicitly selected.

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

The legacy Kaggle pneumonia dataset has image-level class labels only. It cannot supervise lesion boxes, masks, or trustworthy heatmaps. Never display a generated box from that adapter.

The RSNA v2 dataset contains adjudicated pneumonia boxes. The platform may show them only when the untouched-test localization gate passes independently from the classification gate. A classification release does not automatically validate localization.

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

Coordinates are normalized to the source image. When the gate is unavailable or fails, return `localization.validated=false` and show an explicit “localization unavailable” message.

The production localization candidate is the independent Faster R-CNN pipeline in `scripts/train_rsna_detector.py`. It reads the patient-separated `*_cases.jsonl` RSNA manifests, selects its score threshold on validation, and opens the untouched test split only for the final localization report. Run it on Jupyter with:

```bash
python scripts/train_rsna_detector.py \
  --dataset-root /home/jovyan/work/datasets/rsna_pneumonia_2018 \
  --output-dir /home/jovyan/work/medgemma_rsna_v2/detector/rsna_frcnn_v1 \
  --epochs 4 --batch-size 4
```

`jupiter_generate_api.py` loads `detector.pt` only when `quality_report.json` is an untouched-test report with patient separation and both localization thresholds pass (`mean_best_iou >= 0.20`, `hit_rate_iou_0_30 >= 0.25`). Do not lower these thresholds to make a box appear in the UI.

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
