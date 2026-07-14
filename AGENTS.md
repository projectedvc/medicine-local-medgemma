# Instructions for future MedAI agents

Read `docs/MODEL_TRAINING_POLICY.md` before modifying training, inference, model selection, confidence display, or localization.

- `medai-pneumonia-v1` failed the balanced smoke gate and must stay withheld until retrained and re-evaluated.
- Never present self-reported generative confidence as calibrated probability.
- Never render boxes or heatmaps from the class-only Kaggle pneumonia dataset.
- Keep the base and every anatomy/task adapter independently selectable and versioned.
- Run all model training and GPU evaluation on the Jupyter server. Local work is limited to application code and lightweight tests.
