# MedAI 2.0: isolated researcher1 runbook

## Account topology

- `student1`: the current one-GPU production environment. Keep its platform, backend and MedAI 1.0 running.
- `student2`: the second independent one-GPU student environment. Do not repurpose it.
- `researcher1`: the combined profile that must expose both L40S GPUs (about 88 GB VRAM total). All MedAI 2.0 work lives under `~/work/MedAI_researcher1`.

Never stop, restart, overwrite or clean a student profile while working on `researcher1`. Transfer versioned copies with checksums; do not move the originals.

## Seed artifact

MedAI 1.0 is copied from `student1` as an immutable seed. Its expected location is:

```text
~/work/MedAI_researcher1/seed/source/medgemma_rsna_v2/runs/
  rsna_quality_full_lr4e5_1epoch_20260714/final_adapter
```

The seed is merged into a new MedGemma instance in memory. Full training writes only to a new versioned MedAI 2.0 output directory.

## Why this is not “more layers = automatically better”

The two GPUs make full-parameter training technically possible, but quality comes from balanced, patient-separated data and strict untouched tests. Training all weights only on chest images would strengthen chest bias and damage general capabilities. A general candidate therefore requires multiple anatomy families in one curriculum plus at least 25% chest replay to protect the already learned skill.

Localization remains a separate detector/segmentation task. A classification or report model may not invent boxes.

## Required sequence

1. Run the environment preflight. It must report exactly two working CUDA devices.
2. Build a multi-anatomy manifest with `train`, `validation`, and untouched `test` splits separated by patient.
3. Validate the manifest. Do not train when validation fails.
4. Run a 20-step two-GPU smoke test.
5. Compare the smoke checkpoint with base MedGemma and MedAI 1.0 on the same frozen evaluation slice.
6. Only then start the full run.
7. Release as `MedAI 2.0` only if every anatomy gate passes and chest performance does not regress beyond the agreed tolerance.

```bash
cd ~/work/MedAI_researcher1/platform

python scripts/preflight_medai2_researcher1.py \
  --workspace ~/work/MedAI_researcher1 \
  --seed-adapter ~/work/MedAI_researcher1/seed/source/medgemma_rsna_v2/runs/rsna_quality_full_lr4e5_1epoch_20260714/final_adapter \
  --output ~/work/MedAI_researcher1/diagnostics/preflight_medai2.json

python scripts/validate_medai2_manifest.py \
  --manifest ~/work/MedAI_researcher1/data/manifests/medai2_curriculum_v1.jsonl \
  --image-root ~/work/MedAI_researcher1/data \
  --require-test \
  --output ~/work/MedAI_researcher1/diagnostics/manifest_report.json

accelerate launch --config_file configs/accelerate_medai2_fsdp2.yaml \
  scripts/finetune_medgemma_full_fsdp.py \
  --manifest ~/work/MedAI_researcher1/data/manifests/medai2_curriculum_v1.jsonl \
  --image-root ~/work/MedAI_researcher1/data \
  --seed-adapter ~/work/MedAI_researcher1/seed/source/medgemma_rsna_v2/runs/rsna_quality_full_lr4e5_1epoch_20260714/final_adapter \
  --config configs/medai2_full_train.json \
  --output-dir ~/work/MedAI_researcher1/runs/medai2_full_smoke_v1 \
  --smoke
```

Remove `--smoke` and select a new output directory only after the smoke report passes. Never reuse a released directory.
