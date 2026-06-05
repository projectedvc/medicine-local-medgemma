from app.models.enums import Role
from app.models.study import Study
from app.models.user import User


def can_view_study(user: User, study: Study) -> bool:
    if user.role in {Role.admin, Role.radiologist, Role.expert}:
        return True
    if user.role in {Role.physician, Role.student}:
        return study.uploader_id == user.id or study.assigned_radiologist_id == user.id
    return False


def can_upload(user: User) -> bool:
    return user.role in {Role.admin, Role.radiologist, Role.physician, Role.expert}


def can_run_ai(user: User, study: Study) -> bool:
    return can_upload(user) and can_view_study(user, study)


def can_edit_report(user: User, study: Study) -> bool:
    return user.role in {Role.radiologist, Role.expert} and can_view_study(user, study)


def can_confirm_report(user: User, study: Study) -> bool:
    return user.role in {Role.radiologist, Role.expert} and can_view_study(user, study)
