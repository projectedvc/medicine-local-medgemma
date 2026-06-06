from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.security import hash_password
from app.db.session import get_db
from app.models.enums import AuditAction, Role
from app.models.user import User
from app.schemas.user import UserCreate, UserOut, UserUpdate
from app.services.audit import write_audit

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(Role.admin)),
) -> list[User]:
    return db.query(User).order_by(User.id).all()


@router.get("/doctors", response_model=list[UserOut])
def list_doctors(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[User]:
    return (
        db.query(User)
        .filter(User.role.in_([Role.radiologist, Role.physician, Role.expert]))
        .filter(User.is_active.is_(True))
        .order_by(User.id)
        .all()
    )


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.admin)),
) -> User:
    if db.query(User).filter(User.login == payload.login).first():
        raise HTTPException(status_code=409, detail="Пользователь с таким логином уже существует")
    user = User(
        login=payload.login,
        full_name=payload.full_name,
        role=payload.role,
        hashed_password=hash_password(payload.password),
        is_active=payload.is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    write_audit(
        db,
        action=AuditAction.manage_user,
        user=current_user,
        entity_type="user",
        entity_id=user.id,
        details={"login": user.login, "role": user.role.value},
        request=request,
    )
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.admin)),
) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.role is not None:
        user.role = payload.role
    if payload.password is not None:
        user.hashed_password = hash_password(payload.password)
    if payload.is_active is not None:
        user.is_active = payload.is_active
    db.commit()
    db.refresh(user)
    write_audit(
        db,
        action=AuditAction.manage_user,
        user=current_user,
        entity_type="user",
        entity_id=user.id,
        details={"updated": True},
        request=request,
    )
    return user


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
