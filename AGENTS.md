# Instructions for future MedAI agents

Read `docs/MODEL_TRAINING_POLICY.md` before modifying training, inference, model selection, confidence display, or localization.

- `medai-pneumonia-v1` is an experimental user-selectable adapter. Keep its result visible for testing, with an explicit validation warning; do not silently block it.
- `medai-rsna-pneumonia-v2` is the active candidate. Its classification uses label-token likelihood for `normal`, `pneumonia`, and `other_abnormal`; never replace that contract with a free-form diagnostic prompt.
- The v2 adapter may expose an RSNA box only when the untouched-test localization gate in `scripts/jupiter_generate_api.py` passes. Classification and localization gates are independent.
- Never present self-reported generative confidence as calibrated probability.
- Never render boxes or heatmaps from the class-only Kaggle pneumonia dataset (`pneumonia_v1`). RSNA v2 boxes require test-gated provenance.
- Keep the base and every anatomy/task adapter independently selectable and versioned.
- Run all model training and GPU evaluation on the Jupyter server. Local work is limited to application code and lightweight tests.
