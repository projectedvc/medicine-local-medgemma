from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import StudyStatus


class Study(Base):
    __tablename__ = "studies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    accession_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    patient_code: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    study_type: Mapped[str] = mapped_column(String(64), default="ОГК")
    clinical_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[StudyStatus] = mapped_column(Enum(StudyStatus), default=StudyStatus.created, index=True)
    uploader_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    assigned_radiologist_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    uploader = relationship("User", back_populates="uploaded_studies", foreign_keys=[uploader_id])
    assigned_radiologist = relationship("User", foreign_keys=[assigned_radiologist_id])
    images = relationship("ImageFile", back_populates="study", cascade="all, delete-orphan")
    analyses = relationship("AIAnalysis", back_populates="study", cascade="all, delete-orphan")
    report = relationship("Report", back_populates="study", uselist=False, cascade="all, delete-orphan")
    feedback_items = relationship("Feedback", back_populates="study", cascade="all, delete-orphan")


class ImageFile(Base):
    __tablename__ = "image_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    study_id: Mapped[int] = mapped_column(ForeignKey("studies.id"), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    preview_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    file_format: Mapped[str] = mapped_column(String(32), nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    validation_status: Mapped[str] = mapped_column(String(32), default="checked")
    validation_message: Mapped[str] = mapped_column(Text, default="Файл проверен")
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    study = relationship("Study", back_populates="images")
