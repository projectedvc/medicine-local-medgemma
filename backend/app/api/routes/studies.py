from datetime import date, datetime, time, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.enums import AuditAction, Role, StudyStatus
from app.models.study import ImageFile, Study
from app.models.user import User
from app.schemas.study import StudyCreate, StudyDetail, StudyOut, StudyUpdate
from app.services.access import can_upload, can_view_study
from app.services.audit import write_audit
from app.services.image_validation import store_and_validate_upload

router = APIRouter(prefix="/studies", tags=["studies"])


def _study_query(db: Session):
    return db.query(Study).options(
        joinedload(Study.uploader),
        joinedload(Study.assigned_radiologist),
        joinedload(Study.images),
    )


def get_study_or_404(db: Session, study_id: int) -> Study:
    study = _study_query(db).filter(Study.id == study_id).one_or_none()
    if not study:
        raise HTTPException(status_code=404, detail="Исследование не найдено")
    return study


def ensure_study_access(user: User, study: Study) -> None:
    if not can_view_study(user, study):
        raise HTTPException(status_code=403, detail="Нет доступа к исследованию")


@router.get("", response_model=list[StudyOut])
def list_studies(
    search: str | None = Query(default=None, max_length=120),
    status: StudyStatus | None = Query(default=None),
    study_type: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Study]:
    if current_user.role == Role.analyst:
        return []

    query = _study_query(db)
    if current_user.role not in {Role.admin, Role.radiologist, Role.expert}:
        query = query.filter(
            (Study.uploader_id == current_user.id) | (Study.assigned_radiologist_id == current_user.id)
        )
    if status:
        query = query.filter(Study.status == status)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(or_(Study.accession_number.ilike(pattern), Study.patient_code.ilike(pattern)))
    if study_type:
        query = query.filter(Study.study_type == study_type)
    if date_from:
        start = datetime.combine(date_from, time.min, tzinfo=timezone.utc)
        query = query.filter(Study.created_at >= start)
    if date_to:
        end = datetime.combine(date_to, time.max, tzinfo=timezone.utc)
        query = query.filter(Study.created_at <= end)
    return query.order_by(Study.created_at.desc()).limit(limit).all()


@router.post("", response_model=StudyDetail, status_code=201)
def create_study(
    payload: StudyCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Study:
    if not can_upload(current_user):
        raise HTTPException(status_code=403, detail="Нет права создавать исследования")
    study = Study(
        accession_number=f"RX-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid4().hex[:8].upper()}",
        patient_code=payload.patient_code,
        study_type=payload.study_type,
        clinical_note=payload.clinical_note,
        uploader_id=current_user.id,
        assigned_radiologist_id=payload.assigned_radiologist_id,
        status=StudyStatus.created,
    )
    db.add(study)
    db.commit()
    db.refresh(study)
    write_audit(
        db,
        action=AuditAction.create_study,
        user=current_user,
        entity_type="study",
        entity_id=study.id,
        details={"accession_number": study.accession_number},
        request=request,
    )
    return get_study_or_404(db, study.id)


@router.get("/{study_id}", response_model=StudyDetail)
def get_study(
    study_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Study:
    study = get_study_or_404(db, study_id)
    ensure_study_access(current_user, study)
    return study


@router.patch("/{study_id}", response_model=StudyDetail)
def update_study(
    study_id: int,
    payload: StudyUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Study:
    study = get_study_or_404(db, study_id)
    ensure_study_access(current_user, study)
    if current_user.role not in {Role.admin, Role.radiologist, Role.expert} and study.uploader_id != current_user.id:
        raise HTTPException(status_code=403, detail="Нет права изменять исследование")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(study, field, value)
    db.commit()
    db.refresh(study)
    write_audit(
        db,
        action=AuditAction.create_study,
        user=current_user,
        entity_type="study",
        entity_id=study.id,
        details={"updated": True},
        request=request,
    )
    return get_study_or_404(db, study.id)


@router.post("/{study_id}/upload", response_model=StudyDetail)
async def upload_image(
    study_id: int,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Study:
    study = get_study_or_404(db, study_id)
    ensure_study_access(current_user, study)
    if not can_upload(current_user):
        raise HTTPException(status_code=403, detail="Нет права загружать снимки")
    try:
        stored = await store_and_validate_upload(study.id, file)
    except ValueError as exc:
        write_audit(
            db,
            action=AuditAction.validate_file,
            user=current_user,
            entity_type="study",
            entity_id=study.id,
            details={"ok": False, "error": str(exc), "filename": file.filename},
            request=request,
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    image = ImageFile(
        study_id=study.id,
        filename=stored.filename,
        original_filename=stored.original_filename,
        content_type=stored.content_type,
        storage_path=stored.storage_path,
        preview_path=stored.preview_path,
        size_bytes=stored.size_bytes,
        file_format=stored.file_format,
        width=stored.width,
        height=stored.height,
        validation_status="checked",
        validation_message=stored.validation_message,
        metadata_json=stored.metadata_json,
    )
    db.add(image)
    study.status = StudyStatus.ready_for_analysis
    db.commit()
    write_audit(
        db,
        action=AuditAction.upload_file,
        user=current_user,
        entity_type="study",
        entity_id=study.id,
        details={"filename": stored.original_filename, "format": stored.file_format, "size": stored.size_bytes},
        request=request,
    )
    write_audit(
        db,
        action=AuditAction.validate_file,
        user=current_user,
        entity_type="study",
        entity_id=study.id,
        details={"ok": True, "message": stored.validation_message},
        request=request,
    )
    return get_study_or_404(db, study.id)


@router.get("/{study_id}/image/preview")
def preview_image(
    study_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    study = get_study_or_404(db, study_id)
    ensure_study_access(current_user, study)
    image = study.images[-1] if study.images else None
    if not image:
        raise HTTPException(status_code=404, detail="Изображение не загружено")
    path = Path(image.preview_path or image.storage_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Файл изображения не найден")
    media_type = "image/png" if path.suffix.lower() == ".png" else image.content_type or "application/octet-stream"
    return FileResponse(path, media_type=media_type, filename=path.name)
