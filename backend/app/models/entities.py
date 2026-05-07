from datetime import datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base


class Judgment(Base):
    __tablename__ = "judgments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    case_number: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    date_of_order = mapped_column(Date, nullable=True)
    pdf_path: Mapped[str] = mapped_column(Text)
    ocr_used: Mapped[bool] = mapped_column(Boolean, default=False)
    extraction_status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True)
    overall_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    created_at = mapped_column(DateTime, default=datetime.utcnow)
    updated_at = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    extractions: Mapped[list["Extraction"]] = relationship(cascade="all, delete-orphan")
    action_plans: Mapped[list["ActionPlan"]] = relationship(cascade="all, delete-orphan")


class Extraction(Base):
    __tablename__ = "extractions"

    id: Mapped[int] = mapped_column(primary_key=True)
    judgment_id: Mapped[int] = mapped_column(ForeignKey("judgments.id"), index=True)
    field_name: Mapped[str] = mapped_column(String(128), index=True)
    extracted_value = mapped_column(JSON)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_bbox = mapped_column(JSON, nullable=True)
    extraction_source: Mapped[str] = mapped_column(String(32), default="LLM")
    conflict: Mapped[bool] = mapped_column(Boolean, default=False)


class ActionPlan(Base):
    __tablename__ = "action_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    judgment_id: Mapped[int] = mapped_column(ForeignKey("judgments.id"), index=True)
    directive_type: Mapped[str] = mapped_column(String(64), index=True)
    recommended_action: Mapped[str] = mapped_column(Text)
    responsible_authority: Mapped[str | None] = mapped_column(String(255), nullable=True)
    deadline_date = mapped_column(Date, nullable=True)
    priority_level: Mapped[str] = mapped_column(String(32), index=True)
    action_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="DRAFT")


class Verification(Base):
    __tablename__ = "verifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    extraction_id: Mapped[int] = mapped_column(ForeignKey("extractions.id"), index=True)
    reviewer_id: Mapped[str] = mapped_column(String(128), default="prototype-reviewer")
    decision: Mapped[str] = mapped_column(String(32))
    original_value = mapped_column(JSON)
    corrected_value = mapped_column(JSON, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reviewed_at = mapped_column(DateTime, default=datetime.utcnow)


class VerifiedRecord(Base):
    __tablename__ = "verified_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    judgment_id: Mapped[int] = mapped_column(ForeignKey("judgments.id"), index=True)
    case_number: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    urgency_band: Mapped[str] = mapped_column(String(32), index=True)
    appeal_deadline = mapped_column(Date, nullable=True)
    action_summary_en: Mapped[str] = mapped_column(Text)
    action_summary_kn: Mapped[str | None] = mapped_column(Text, nullable=True)
    audit_trail = mapped_column(JSON, default=list)
    verified_at = mapped_column(DateTime, default=datetime.utcnow)
    reviewer_id: Mapped[str] = mapped_column(String(128), default="prototype-reviewer")
