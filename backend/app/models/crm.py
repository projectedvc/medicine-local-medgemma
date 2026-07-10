from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


crm_participants = Table(
    "crm_participants",
    Base.metadata,
    Column("record_id", ForeignKey("crm_records.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)


crm_study_links = Table(
    "crm_study_links",
    Base.metadata,
    Column("record_id", ForeignKey("crm_records.id", ondelete="CASCADE"), primary_key=True),
    Column("study_id", ForeignKey("studies.id", ondelete="CASCADE"), primary_key=True),
)


class CRMRecord(Base):
    __tablename__ = "crm_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_code: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    contact_type: Mapped[str] = mapped_column(String(80), default="consultation")
    status: Mapped[str] = mapped_column(String(80), default="active", index=True)
    priority: Mapped[str] = mapped_column(String(40), default="normal", index=True)
    summary: Mapped[str] = mapped_column(String(240), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    next_step: Mapped[str | None] = mapped_column(String(240), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    created_by = relationship("User", foreign_keys=[created_by_id])
    updated_by = relationship("User", foreign_keys=[updated_by_id])
    participants = relationship("User", secondary=crm_participants, order_by="User.full_name")
    studies = relationship("Study", secondary=crm_study_links, order_by="Study.created_at.desc()")
    activities = relationship(
        "CRMActivity",
        back_populates="record",
        cascade="all, delete-orphan",
        order_by="CRMActivity.created_at.desc()",
    )


class CRMActivity(Base):
    __tablename__ = "crm_activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    record_id: Mapped[int] = mapped_column(ForeignKey("crm_records.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    activity_type: Mapped[str] = mapped_column(String(40), default="note", index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    record = relationship("CRMRecord", back_populates="activities")
    author = relationship("User")
