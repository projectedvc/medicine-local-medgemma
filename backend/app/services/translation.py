from __future__ import annotations

from functools import lru_cache

import httpx

from app.core.config import settings


SUPPORTED_TARGETS = {"ru", "kk"}


def _provider() -> str:
    return (settings.translation_provider or "local").strip().casefold()


def _chunk_text(text: str, max_chars: int) -> list[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    current = ""
    for paragraph in text.splitlines():
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        next_value = f"{current}\n{paragraph}".strip() if current else paragraph
        if len(next_value) <= max_chars:
            current = next_value
            continue
        if current:
            chunks.append(current)
        current = paragraph
    if current:
        chunks.append(current)
    return chunks or [text[:max_chars]]


@lru_cache(maxsize=512)
def _google_translate_cached(text: str, target_lang: str) -> str | None:
    params = {
        "client": "gtx",
        "sl": "auto",
        "tl": target_lang,
        "dt": "t",
        "q": text,
    }
    try:
        with httpx.Client(timeout=settings.translation_timeout_seconds) as client:
            response = client.get("https://translate.googleapis.com/translate_a/single", params=params)
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return None

    try:
        translated = "".join(part[0] for part in payload[0] if part and part[0])
    except (TypeError, IndexError):
        return None
    translated = translated.strip()
    return translated or None


def translate_text(text: str, target_lang: str) -> str | None:
    target = (target_lang or "").strip().lower()
    if target not in SUPPORTED_TARGETS:
        return None
    provider = _provider()
    if provider in {"", "off", "none", "disabled", "local"}:
        return None
    if provider != "google":
        return None

    chunks = _chunk_text(text, max(500, settings.translation_max_chars))
    translated_chunks: list[str] = []
    for chunk in chunks:
        translated = _google_translate_cached(chunk, target)
        if not translated:
            return None
        translated_chunks.append(translated)
    return "\n".join(translated_chunks).strip() or None
