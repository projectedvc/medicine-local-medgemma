import json
import uuid
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import numpy as np
import pydicom
from fastapi import UploadFile
from PIL import Image

from app.core.config import settings


ALLOWED_EXTENSIONS = {".dcm", ".dicom", ".jpg", ".jpeg", ".png"}


@dataclass
class StoredImage:
    filename: str
    original_filename: str
    content_type: str | None
    storage_path: str
    preview_path: str | None
    size_bytes: int
    file_format: str
    width: int | None
    height: int | None
    validation_message: str
    metadata_json: str | None = None


def _safe_suffix(filename: str) -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError("Недопустимый формат файла. Разрешены DICOM, JPEG и PNG.")
    return suffix


def _normalize_dicom_pixels(dataset: pydicom.dataset.FileDataset) -> Image.Image:
    pixels = dataset.pixel_array.astype(np.float32)
    pixels -= float(np.min(pixels))
    maximum = float(np.max(pixels))
    if maximum > 0:
        pixels /= maximum
    pixels *= 255.0
    if getattr(dataset, "PhotometricInterpretation", "") == "MONOCHROME1":
        pixels = 255.0 - pixels
    return Image.fromarray(pixels.astype(np.uint8)).convert("L")


def _validate_raster(data: bytes) -> tuple[int, int]:
    with Image.open(BytesIO(data)) as image:
        image.verify()
    with Image.open(BytesIO(data)) as image:
        width, height = image.size
    if width <= 0 or height <= 0:
        raise ValueError("Файл изображения не содержит читаемого растра.")
    return width, height


def _validate_dicom(data: bytes, preview_path: Path) -> tuple[int, int, str]:
    dataset = pydicom.dcmread(BytesIO(data), force=True)
    if not hasattr(dataset, "PixelData"):
        raise ValueError("DICOM не содержит изображения PixelData.")
    preview = _normalize_dicom_pixels(dataset)
    preview.save(preview_path, format="PNG")
    metadata = {
        "Modality": str(getattr(dataset, "Modality", "")),
        "BodyPartExamined": str(getattr(dataset, "BodyPartExamined", "")),
        "StudyDescription": str(getattr(dataset, "StudyDescription", "")),
        "Rows": int(getattr(dataset, "Rows", 0) or 0),
        "Columns": int(getattr(dataset, "Columns", 0) or 0),
    }
    return preview.width, preview.height, json.dumps(metadata, ensure_ascii=False)


async def store_and_validate_upload(study_id: int, upload: UploadFile) -> StoredImage:
    original_filename = upload.filename or "image"
    suffix = _safe_suffix(original_filename)
    data = await upload.read()
    if not data:
        raise ValueError("Файл пустой.")
    if len(data) > settings.max_upload_bytes:
        raise ValueError(f"Размер файла превышает лимит {settings.max_upload_mb} MB.")

    study_dir = settings.upload_dir / str(study_id)
    study_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{suffix}"
    storage_path = study_dir / stored_name
    preview_path: Path | None = None
    metadata_json: str | None = None

    if suffix in {".jpg", ".jpeg", ".png"}:
        width, height = _validate_raster(data)
        file_format = suffix.lstrip(".").upper()
        preview_path = storage_path
    else:
        file_format = "DICOM"
        preview_path = study_dir / f"{uuid.uuid4().hex}.png"
        width, height, metadata_json = _validate_dicom(data, preview_path)

    storage_path.write_bytes(data)
    return StoredImage(
        filename=stored_name,
        original_filename=original_filename,
        content_type=upload.content_type,
        storage_path=str(storage_path),
        preview_path=str(preview_path) if preview_path else None,
        size_bytes=len(data),
        file_format=file_format,
        width=width,
        height=height,
        validation_message="Формат, размер и читаемость изображения проверены",
        metadata_json=metadata_json,
    )
