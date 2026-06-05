from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import AuditAction, Role
from app.models.pathology import Pathology
from app.models.user import User
from app.schemas.pathology import PathologyCreate, PathologyOut
from app.services.audit import write_audit

router = APIRouter(prefix="/pathologies", tags=["pathologies"])


@router.get("", response_model=list[PathologyOut])
def list_pathologies(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Pathology]:
    return db.query(Pathology).order_by(Pathology.title).all()


@router.post("", response_model=PathologyOut, status_code=status.HTTP_201_CREATED)
def create_pathology(
    payload: PathologyCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.admin, Role.expert)),
) -> Pathology:
    if db.query(Pathology).filter(Pathology.slug == payload.slug).first():
        raise HTTPException(status_code=409, detail="Такой элемент справочника уже существует")
    item = Pathology(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    write_audit(
        db,
        action=AuditAction.manage_reference,
        user=current_user,
        entity_type="pathology",
        entity_id=item.id,
        details={"slug": item.slug},
        request=request,
    )
    return item


@router.put("/{pathology_id}", response_model=PathologyOut)
def update_pathology(
    pathology_id: int,
    payload: PathologyCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.admin, Role.expert)),
) -> Pathology:
    item = db.get(Pathology, pathology_id)
    if not item:
        raise HTTPException(status_code=404, detail="Элемент справочника не найден")
    for field, value in payload.model_dump().items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    write_audit(
        db,
        action=AuditAction.manage_reference,
        user=current_user,
        entity_type="pathology",
        entity_id=item.id,
        details={"slug": item.slug, "updated": True},
        request=request,
    )
    return item
