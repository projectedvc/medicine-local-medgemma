# Jupiter + Vercel deployment

Сейчас Vercel-фронт вызывает не AI напрямую, а API приложения:

- `POST /api/auth/login`
- `POST /api/studies`
- `POST /api/studies/{id}/upload`
- `POST /api/studies/{id}/ai/run`

Поэтому публичный ngrok-домен, указанный в `vercel.json`, должен вести на backend проекта `medicine`, а не на отдельный notebook API с одним `/generate`.

## Правильная схема

```text
Vercel frontend
  -> /api/*
  -> ngrok domain
  -> medicine backend on port 8000
  -> AI_SERVICE_URL=http://127.0.0.1:8001/generate
  -> Jupiter model API on port 8001
```

## 1. AI model API на Jupiter

В notebook-коде с моделью оставьте `/generate`, но поменяйте порт с `8000` на `8001`:

```python
from scripts.jupiter_generate_api import start_api

# Run this after `model` and `processor` are loaded.
start_api(model, processor, port=8001)
```

Если видите `422` с текстом `Input should be a valid dictionary`, значит endpoint ожидает JSON, а запрос отправлен как `data=...` / form-urlencoded. Готовый `scripts/jupiter_generate_api.py` принимает оба формата.

Проверка без картинки:

```python
import requests

r = requests.post(
    "http://127.0.0.1:8001/generate",
    json={"prompt": "Analyze this chest X-ray. Return compact JSON."},
)
print(r.status_code)
print(r.text[:1000])
```

Проверка с картинкой:

```python
import requests

with open("test.jpg", "rb") as handle:
    r = requests.post(
        "http://127.0.0.1:8001/generate",
        data={"prompt": "Analyze this chest X-ray. Return compact JSON."},
        files={"image": ("test.jpg", handle, "image/jpeg")},
    )

print(r.status_code)
print(r.text[:1000])
```

## 2. Medicine backend на Jupiter

В отдельной ячейке/терминале на Jupiter запустите backend проекта:

```python
import os, subprocess, threading, time

PROJECT_DIR = "/path/to/medicine/backend"  # путь к backend на Jupiter
NGROK_TOKEN = "YOUR_NGROK_TOKEN"
NGROK_DOMAIN = "shiny-net-slimy.ngrok-free.dev"

os.environ["AI_SERVICE_URL"] = "http://127.0.0.1:8001/generate"
os.environ["AI_ALLOW_MOCK"] = "false"
os.environ["ALLOWED_ORIGINS"] = "https://aimedicine.vercel.app,http://localhost:5173,http://127.0.0.1:5173"
os.environ.setdefault("JWT_SECRET", "change-this-long-random-value")

def run_backend():
    subprocess.run(
        ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd=PROJECT_DIR,
        env=os.environ.copy(),
    )

def run_ngrok():
    subprocess.run(f"/tmp/ngrok config add-authtoken {NGROK_TOKEN}", shell=True)
    subprocess.run(["/tmp/ngrok", "http", "--url", NGROK_DOMAIN, "8000"])

threading.Thread(target=run_backend, daemon=True).start()
time.sleep(3)
threading.Thread(target=run_ngrok, daemon=True).start()
print(f"Public backend: https://{NGROK_DOMAIN}")
```

## 3. Проверка

Эти проверки должны проходить:

```python
import requests

headers = {"ngrok-skip-browser-warning": "true"}

print(requests.get("https://shiny-net-slimy.ngrok-free.dev/health", headers=headers).text)

r = requests.post(
    "https://shiny-net-slimy.ngrok-free.dev/api/auth/login",
    json={"login": "radiologist", "password": "radio123"},
    headers=headers,
)
print(r.status_code, r.text)
```

Правильный `/health` для backend выглядит примерно так:

```json
{"status":"ok","service":"Radiology AI Assistant"}
```

Если `/health` возвращает только `{"status":"ok"}`, значит на домене все еще висит маленький AI-service, а не backend `medicine`.

## Если Jupyter пишет `IOPub data rate exceeded`

Это лимит вывода notebook, а не отдельная ошибка FastAPI. Обычно он срабатывает, когда ячейка печатает слишком большой ответ модели или полный HTTP response.

Для проверки не печатайте весь `r.text`, а ограничивайте вывод:

```python
print(r.status_code)
print(r.text[:1000])
```

В AI prompt просите модель вернуть только компактный JSON, а в `model.generate(...)` держите небольшой `max_new_tokens`, например `128` или `256`. Если backend запущен с `AI_ALLOW_MOCK=true`, запрос в Jupiter AI вообще не пойдет: backend сразу вернет mock-результат.
