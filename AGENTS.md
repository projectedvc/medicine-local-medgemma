# Instructions for future MedAI agents

Read `docs/MODEL_TRAINING_POLICY.md` before modifying training, inference, model selection, confidence display, or localization.

For all two-GPU or MedAI 2.0 work, also read `docs/RESEARCHER1_MEDAI2_RUNBOOK.md`.

- `student1` and `student2` are independent single-GPU environments and must remain usable.
- `researcher1` is their combined two-GPU profile. Put every new artifact under `~/work/MedAI_researcher1`; never modify pre-existing researcher folders.
- MedAI 1.0 is an immutable seed/control. Merge a copied adapter into a new candidate; never overwrite the original adapter or its reports.
- Full-parameter training requires a validated multi-anatomy curriculum, a two-GPU smoke run and comparison against both base MedGemma and MedAI 1.0.
- Do not start training if `nvidia-smi`, CUDA tensor smoke, patient separation, manifest validation or the release-test reservation fails.

- `medai-pneumonia-v1` is an experimental user-selectable adapter. Keep its result visible for testing, with an explicit validation warning; do not silently block it.
- `medai-rsna-pneumonia-v2` is the active candidate. Its classification uses label-token likelihood for `normal`, `pneumonia`, and `other_abnormal`; never replace that contract with a free-form diagnostic prompt.
- The v2 adapter may expose an RSNA box only when the untouched-test localization gate in `scripts/jupiter_generate_api.py` passes. Classification and localization gates are independent.
- Never present self-reported generative confidence as calibrated probability.
- Never render boxes or heatmaps from the class-only Kaggle pneumonia dataset (`pneumonia_v1`). RSNA v2 boxes require test-gated provenance.
- Keep the base and every anatomy/task adapter independently selectable and versioned.
- Run all model training and GPU evaluation on the Jupyter server. Local work is limited to application code and lightweight tests.
