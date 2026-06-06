"""
Drop-in MedGemma FastAPI server for a Jupiter/Jupyter notebook.

Usage after model and processor are loaded:

    from scripts.jupiter_generate_api import start_api
    start_api(model, processor, port=8001)

Manual checks:

    import requests
    r = requests.post(
        "http://127.0.0.1:8001/generate",
        json={"prompt": "Analyze this chest X-ray. Return compact JSON."},
    )
    print(r.status_code, r.text[:1000])

    with open("test.jpg", "rb") as handle:
        r = requests.post(
            "http://127.0.0.1:8001/generate",
            data={"prompt": "Analyze this chest X-ray. Return compact JSON."},
            files={"image": ("test.jpg", handle, "image/jpeg")},
        )
    print(r.status_code, r.text[:1000])
"""

from __future__ import annotations

import io
import threading
from typing import Any

import torch
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from starlette.datastructures import UploadFile as StarletteUploadFile


DEFAULT_PROMPT = (
    "Analyze this chest radiology image. Return only compact JSON: "
    '{"prediction":"normal|pneumonia|pneumothorax|pleural_effusion|atelectasis",'
    '"confidence":0.0,"top3":{"class":0.0}}. No extra text.'
)


async def _read_request(request: Request) -> tuple[str, Image.Image | None]:
    content_type = request.headers.get("content-type", "").casefold()
    prompt = ""
    upload: Any = None

    if "application/json" in content_type:
        payload = await request.json()
        if not isinstance(payload, dict):
            raise HTTPException(status_code=422, detail="JSON body must be an object.")
        prompt = str(payload.get("prompt") or DEFAULT_PROMPT)
    elif "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        prompt = str(form.get("prompt") or DEFAULT_PROMPT)
        upload = form.get("image") or form.get("file")
    else:
        body = (await request.body()).decode("utf-8", errors="ignore").strip()
        prompt = body or DEFAULT_PROMPT

    if not prompt:
        raise HTTPException(status_code=422, detail="prompt is required.")

    if not isinstance(upload, StarletteUploadFile):
        return prompt, None

    data = await upload.read()
    if not data:
        return prompt, None
    try:
        return prompt, Image.open(io.BytesIO(data)).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"image is not readable: {exc}") from exc


def _build_messages(prompt: str, image: Image.Image | None) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = []
    if image is not None:
        content.append({"type": "image", "image": image})
    content.append({"type": "text", "text": prompt})
    return [{"role": "user", "content": content}]


def create_app(model: Any, processor: Any, max_new_tokens: int = 192) -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "medgemma-generate"}

    @app.post("/generate")
    async def generate(request: Request) -> dict[str, str]:
        prompt, pil_image = await _read_request(request)
        messages = _build_messages(prompt, pil_image)

        inputs = processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_tensors="pt",
        ).to(model.device)

        with torch.inference_mode():
            outputs = model.generate(inputs, max_new_tokens=max_new_tokens, do_sample=False)

        response = processor.decode(outputs[0], skip_special_tokens=True)
        return {"response": response[:4000]}

    return app


def start_api(model: Any, processor: Any, port: int = 8001, max_new_tokens: int = 192) -> threading.Thread:
    app = create_app(model, processor, max_new_tokens=max_new_tokens)

    def run() -> None:
        uvicorn.run(app, host="0.0.0.0", port=port)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    print(f"AI API started on http://127.0.0.1:{port}")
    return thread
