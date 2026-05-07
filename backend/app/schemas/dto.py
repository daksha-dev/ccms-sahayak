from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


Decision = Literal["APPROVED", "EDITED", "REJECTED"]
RejectionReason = Literal["wrong extraction", "ambiguous", "not applicable"]


class FieldCoord(BaseModel):
    page: int
    bbox: list[float]


class Directive(BaseModel):
    directive_text: str
    directive_type: str
    responsible_party: str | None = None
    timeline_explicit: str | None = None
    timeline_inferred: str | None = None


class ExtractionJSON(BaseModel):
    case_number: str | None = None
    date_of_order: date | None = None
    court_name: str | None = None
    parties_petitioner: list[str] = Field(default_factory=list)
    parties_respondent: list[str] = Field(default_factory=list)
    responsible_department: str | None = None
    directives: list[Directive] = Field(default_factory=list)
    limitation_period_days: int | None = None
    appeal_deadline_date: date | None = None
    urgency_band: str | None = None
    nature_of_order: str | None = None
    coordinate_map: dict[str, list[FieldCoord]] = Field(default_factory=dict)
    confidence_scores: dict[str, float] = Field(default_factory=dict)


class ActionPlanItem(BaseModel):
    directive_type: str
    recommended_action: str
    responsible_authority: str | None = None
    deadline_date: date | None = None
    priority_level: str
    notes: str | None = None


class FieldDecisionRequest(BaseModel):
    decision: Decision
    corrected_value: Any | None = None
    rejection_reason: RejectionReason | None = None


class FieldDecisionResponse(BaseModel):
    extraction_id: int
    decision: Decision
    reviewed_at: datetime


class UploadResponse(BaseModel):
    job_id: int
    extraction_status: str
    overall_confidence: float
    ocr_used: bool


class ReviewField(BaseModel):
    id: int
    field_name: str
    extracted_value: Any
    confidence_score: float
    source_page: int | None
    source_bbox: Any | None
    extraction_source: str
    conflict: bool
    decision: str | None = None


class ReviewResponse(BaseModel):
    job_id: int
    pdf_url: str
    extraction_status: str
    overall_confidence: float
    fields: list[ReviewField]
    action_plan: list[ActionPlanItem]


class VerifyResponse(BaseModel):
    job_id: int
    status: str
    verified_record_id: int


class DashboardRecord(BaseModel):
    id: int
    judgment_id: int
    case_number: str | None
    department: str | None
    urgency_band: str
    appeal_deadline: date | None
    action_summary_en: str
    action_summary_kn: str | None
    verified_at: datetime
    audit_trail: list[dict[str, Any]] = Field(default_factory=list)


class DashboardResponse(BaseModel):
    records: list[DashboardRecord]
    total: int
    page: int
    limit: int


class DashboardStats(BaseModel):
    total_active_cases: int
    red_urgency: int
    amber_urgency: int
    pending_appeals: int
