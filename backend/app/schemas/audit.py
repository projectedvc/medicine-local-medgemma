from datetime import datetime

from app.models.enums import AuditAction
from app.schemas.common import ORMModel
from app.schemas.user import UserOut


class AuditLogOut(ORMModel):
    id: int
    user: UserOut | None = None
    action: AuditAction
    entity_type: str | None
    entity_id: int | None
    details_json: str | None
    ip_address: str | None
    created_at: datetime
