from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.crm import CRMRecord
from app.models.enums import Role
from app.models.user import User
from app.schemas.crm import CRMRecordCreate, CRMRecordOut, CRMRecordUpdate

router = APIRouter(prefix="/crm", tags=["crm"])


def _can_use_crm(user: User) -> bool:
    return user.role in {Role.admin, Role.radiologist, Role.physician, Role.expert}


def _query(db: Session):
    return db.query(CRMRecord).options(joinedload(CRMRecord.created_by), joinedload(CRMRecord.updated_by))


def _record_or_404(db: Session, record_id: int) -> CRMRecord:
    record = _query(db).filter(CRMRecord.id == record_id).one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="CRM запись не найдена")
    return record


@router.get("", response_model=list[CRMRecordOut])
def list_records(
    patient_code: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=80, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CRMRecord]:
    if not _can_use_crm(current_user):
        raise HTTPException(status_code=403, detail="Нет доступа к CRM")
    query = _query(db)
    if patient_code:
        query = query.filter(CRMRecord.patient_code.ilike(f"%{patient_code}%"))
    if status:
        query = query.filter(CRMRecord.status == status)
    return query.order_by(CRMRecord.updated_at.desc()).limit(limit).all()


@router.post("", response_model=CRMRecordOut, status_code=201)
def create_record(
    payload: CRMRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CRMRecord:
    if not _can_use_crm(current_user):
        raise HTTPException(status_code=403, detail="Нет права создавать CRM записи")
    record = CRMRecord(**payload.model_dump(), created_by_id=current_user.id, updated_by_id=current_user.id)
    db.add(record)
    db.commit()
    return _record_or_404(db, record.id)


@router.patch("/{record_id}", response_model=CRMRecordOut)
def update_record(
    record_id: int,
    payload: CRMRecordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CRMRecord:
    if not _can_use_crm(current_user):
        raise HTTPException(status_code=403, detail="Нет права изменять CRM записи")
    record = _record_or_404(db, record_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    record.updated_by_id = current_user.id
    db.commit()
    return _record_or_404(db, record.id)


@router.delete("/{record_id}", status_code=204)
def delete_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    if current_user.role not in {Role.admin, Role.radiologist, Role.expert}:
        raise HTTPException(status_code=403, detail="Нет права удалять CRM записи")
    record = _record_or_404(db, record_id)
    db.delete(record)
    db.commit()
