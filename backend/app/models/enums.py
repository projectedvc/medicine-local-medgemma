from enum import Enum


class Role(str, Enum):
    admin = "admin"
    radiologist = "radiologist"
    physician = "physician"
    expert = "expert"
    student = "student"
    analyst = "analyst"


ROLE_LABELS: dict[Role, str] = {
    Role.admin: "Администратор",
    Role.radiologist: "Рентгенолог",
    Role.physician: "Врач-пользователь",
    Role.expert: "Эксперт",
    Role.student: "Студент",
    Role.analyst: "Аналитик",
}


class StudyStatus(str, Enum):
    created = "created"
    uploaded = "uploaded"
    checked = "checked"
    ready_for_analysis = "ready_for_analysis"
    analyzing = "analyzing"
    ai_completed = "ai_completed"
    draft_ready = "draft_ready"
    confirmed = "confirmed"
    exported = "exported"
    failed = "failed"


class AIJobStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class FindingClass(str, Enum):
    normal = "normal"
    pneumonia = "pneumonia"
    other_abnormal = "other_abnormal"
    pleural_effusion = "pleural_effusion"
    pneumothorax = "pneumothorax"
    atelectasis = "atelectasis"


FINDING_LABELS: dict[FindingClass, str] = {
    FindingClass.normal: "Норма",
    FindingClass.pneumonia: "Пневмония",
    FindingClass.other_abnormal: "Другая патология",
    FindingClass.pleural_effusion: "Плевральный выпот",
    FindingClass.pneumothorax: "Пневмоторакс",
    FindingClass.atelectasis: "Ателектаз",
}


class FeedbackType(str, Enum):
    false_positive = "false_positive"
    false_negative = "false_negative"
    wrong_region = "wrong_region"
    other = "other"


class AuditAction(str, Enum):
    login = "login"
    create_study = "create_study"
    upload_file = "upload_file"
    validate_file = "validate_file"
    run_ai = "run_ai"
    create_draft = "create_draft"
    edit_report = "edit_report"
    confirm_report = "confirm_report"
    export_report = "export_report"
    create_feedback = "create_feedback"
    manage_reference = "manage_reference"
    manage_user = "manage_user"
