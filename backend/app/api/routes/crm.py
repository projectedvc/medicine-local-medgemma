from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.crm import CRMActivity, CRMRecord
from app.models.enums import Role
from app.models.study import Study
from app.models.user import User
from app.schemas.crm import CRMActivityCreate, CRMActivityOut, CRMRecordCreate, CRMRecordOut, CRMRecordUpdate
from app.services.access import can_view_study

router = APIRouter(prefix="/crm", tags=["crm"])


CRM_VIEW_ROLES = {Role.admin, Role.radiologist, Role.physician, Role.expert, Role.analyst}
CRM_MANAGE_ROLES = {Role.admin, Role.radiologist, Role.physician, Role.expert}


def _can_view_crm(user: User) -> bool:
    return user.role in CRM_VIEW_ROLES


def _can_manage_crm(user: User) -> bool:
    return user.role in CRM_MANAGE_ROLES


def _query(db: Session):
    return db.query(CRMRecord).options(
        joinedload(CRMRecord.created_by),
        joinedload(CRMRecord.updated_by),
        joinedload(CRMRecord.participants),
        joinedload(CRMRecord.studies),
        joinedload(CRMRecord.activities).joinedload(CRMActivity.author),
    )


def _record_or_404(db: Session, record_id: int) -> CRMRecord:
    record = _query(db).filter(CRMRecord.id == record_id).one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="CRM запись не найдена")
    return record


def _resolve_participants(db: Session, participant_ids: list[int]) -> list[User]:
    ids = list(dict.fromkeys(participant_ids))
    if not ids:
        return []
    users = db.query(User).filter(User.id.in_(ids), User.is_active.is_(True)).all()
    if len(users) != len(ids):
        raise HTTPException(status_code=400, detail="Один или несколько участников CRM не найдены")
    if any(user.role not in CRM_VIEW_ROLES for user in users):
        raise HTTPException(status_code=400, detail="К CRM можно привязать только сотрудников отдела")
    return users


def _resolve_studies(db: Session, study_ids: list[int], current_user: User) -> list[Study]:
    ids = list(dict.fromkeys(study_ids))
    if not ids:
        return []
    studies = db.query(Study).filter(Study.id.in_(ids)).all()
    if len(studies) != len(ids):
        raise HTTPException(status_code=400, detail="Одно или несколько исследований не найдены")
    if any(not can_view_study(current_user, study) for study in studies):
        raise HTTPException(status_code=403, detail="Нет доступа к выбранному исследованию")
    return studies


def _add_activity(db: Session, record: CRMRecord, user: User, activity_type: str, content: str) -> None:
    db.add(
        CRMActivity(
            record_id=record.id,
            author_id=user.id,
            activity_type=activity_type,
            content=content,
        )
    )


@router.get("", response_model=list[CRMRecordOut])
def list_records(
    patient_code: str | None = Query(default=None),
    search: str | None = Query(default=None),
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    participant_id: int | None = Query(default=None),
    limit: int = Query(default=80, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CRMRecord]:
    if not _can_view_crm(current_user):
        raise HTTPException(status_code=403, detail="Нет доступа к CRM")
    query = _query(db)
    if patient_code:
        query = query.filter(CRMRecord.patient_code.ilike(f"%{patient_code}%"))
    if status:
        query = query.filter(CRMRecord.status == status)
    if priority:
        query = query.filter(CRMRecord.priority == priority)
    if participant_id:
        query = query.filter(CRMRecord.participants.any(User.id == participant_id))
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                CRMRecord.patient_code.ilike(pattern),
                CRMRecord.summary.ilike(pattern),
                CRMRecord.note.ilike(pattern),
                CRMRecord.next_step.ilike(pattern),
            )
        )
    return query.order_by(CRMRecord.updated_at.desc()).limit(limit).all()


@router.post("", response_model=CRMRecordOut, status_code=201)
def create_record(
    payload: CRMRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CRMRecord:
    if not _can_manage_crm(current_user):
        raise HTTPException(status_code=403, detail="Нет права создавать CRM записи")
    data = payload.model_dump(exclude={"participant_ids", "linked_study_ids"})
    record = CRMRecord(**data, created_by_id=current_user.id, updated_by_id=current_user.id)
    record.participants = _resolve_participants(db, payload.participant_ids) or [current_user]
    record.studies = _resolve_studies(db, payload.linked_study_ids, current_user)
    db.add(record)
    db.flush()
    _add_activity(db, record, current_user, "created", f"CRM запись создана: {record.summary}")
    db.commit()
    return _record_or_404(db, record.id)


@router.patch("/{record_id}", response_model=CRMRecordOut)
def update_record(
    record_id: int,
    payload: CRMRecordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CRMRecord:
    if not _can_manage_crm(current_user):
        raise HTTPException(status_code=403, detail="Нет права изменять CRM записи")
    record = _record_or_404(db, record_id)
    changes = payload.model_dump(exclude_unset=True)
    participant_ids = changes.pop("participant_ids", None)
    linked_study_ids = changes.pop("linked_study_ids", None)
    for field, value in changes.items():
        setattr(record, field, value)
    if participant_ids is not None:
        record.participants = _resolve_participants(db, participant_ids)
    if linked_study_ids is not None:
        record.studies = _resolve_studies(db, linked_study_ids, current_user)
    record.updated_by_id = current_user.id
    changed_fields = ", ".join(changes) or "связи"
    _add_activity(db, record, current_user, "updated", f"Обновлены поля: {changed_fields}")
    db.commit()
    return _record_or_404(db, record.id)


@router.post("/{record_id}/activities", response_model=CRMActivityOut, status_code=status.HTTP_201_CREATED)
def create_activity(
    record_id: int,
    payload: CRMActivityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CRMActivity:
    if not _can_manage_crm(current_user):
        raise HTTPException(status_code=403, detail="Нет права добавлять действия в CRM")
    record = _record_or_404(db, record_id)
    activity = CRMActivity(
        record_id=record.id,
        author_id=current_user.id,
        activity_type=payload.activity_type,
        content=payload.content,
    )
    record.updated_by_id = current_user.id
    db.add(activity)
    db.commit()
    return (
        db.query(CRMActivity)
        .options(joinedload(CRMActivity.author))
        .filter(CRMActivity.id == activity.id)
        .one()
    )


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
