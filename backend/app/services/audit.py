import json

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.enums import AuditAction
from app.models.user import User


def write_audit(
    db: Session,
    *,
    action: AuditAction,
    user: User | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    details: dict | None = None,
    request: Request | None = None,
) -> AuditLog:
    ip_address = request.client.host if request and request.client else None
    audit = AuditLog(
        user_id=user.id if user else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details_json=json.dumps(details or {}, ensure_ascii=False),
        ip_address=ip_address,
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)
    return audit
