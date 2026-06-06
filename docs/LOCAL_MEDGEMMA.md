# Local MedGemMA 1.5

This copy is configured to use `google/medgemma-1.5-4b-it` locally.

## Download

Accept the model terms on Hugging Face for the account that owns your token, then run:

```powershell
cd C:\Users\USER\Desktop\projects\medicine-local-medgemma
$env:HF_TOKEN="<your token>"
.\backend\.venv\Scripts\python.exe .\scripts\download_medgemma.py
Remove-Item Env:\HF_TOKEN
```

The model is stored in `models/medgemma-1.5-4b-it`. This folder is ignored by git.

## Run

One-click launcher with visible logs:

```powershell
cd C:\Users\USER\Desktop\projects\medicine-local-medgemma
.\run_local_medgemma.bat
```

It opens separate backend and frontend log windows and also writes logs to `logs/backend.log` and `logs/frontend.log`.
Frontend runs on `http://127.0.0.1:3000`.

Public ngrok link:

```powershell
cd C:\Users\USER\Desktop\projects\medicine-local-medgemma
$env:NGROK_AUTHTOKEN="<your ngrok token>"
.\run_local_medgemma.bat --public
```

If ngrok is already configured, the token line is optional. Copy the `Forwarding` URL from the ngrok window.

Backend:

```powershell
cd C:\Users\USER\Desktop\projects\medicine-local-medgemma\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd C:\Users\USER\Desktop\projects\medicine-local-medgemma\frontend
npm run dev -- --host 0.0.0.0 --port 3000
```

## Fine-tuning data format

Use JSONL rows like this:

```json
{"image":"study-001.png","clinical_note":"fever and cough","answer":"Findings... Impression..."}
```

Then start a small LoRA run:

```powershell
cd C:\Users\USER\Desktop\projects\medicine-local-medgemma\backend
.\.venv\Scripts\python.exe ..\scripts\finetune_medgemma_lora.py --train-jsonl ..\data\train.jsonl --image-root ..\data\images
```

This setup enables 4-bit loading by default through `LOCAL_MEDGEMMA_LOAD_IN_4BIT=true`.
With an 8 GB GPU, keep batch size at `1`, use small datasets first, and expect slow training.
