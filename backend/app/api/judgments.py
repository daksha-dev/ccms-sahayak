import shutil
from datetime import date
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.models.entities import ActionPlan, Extraction, Judgment, Verification, VerifiedRecord
from app.schemas.dto import (
    ActionPlanItem,
    FieldDecisionRequest,
    FieldDecisionResponse,
    ReviewField,
    ReviewResponse,
    UploadResponse,
    VerifyResponse,
)
from app.services.action_planner import generate_action_plan
from app.services.extractor import extract_judgment
from app.services.sarvam_client import SarvamClient

router = APIRouter()


def _save_upload(upload: UploadFile, storage_dir: Path) -> Path:
    if upload.content_type != "application/pdf" and not upload.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF judgments are supported.")
    target = storage_dir / upload.filename
    with target.open("wb") as out:
        shutil.copyfileobj(upload.file, out)
    return target


def _serializable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_serializable(item) for item in value]
    return value


def _as_date(value: Any) -> date | None:
    if value is None or isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        return date.fromisoformat(value)
    return None


@router.post("/upload", response_model=UploadResponse)
async def upload_judgment(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> UploadResponse:
    path = _save_upload(file, settings.pdf_storage_dir)
    judgment = Judgment(pdf_path=str(path), extraction_status="PENDING")
    db.add(judgment)
    db.commit()
    db.refresh(judgment)

    try:
        extraction, field_meta, ocr_used, confidence = await extract_judgment(path, settings)
        action_items = await generate_action_plan(extraction, settings)
    except RuntimeError as exc:
        judgment.extraction_status = "FLAGGED"
        db.commit()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        judgment.extraction_status = "FLAGGED"
        db.commit()
        body = exc.response.text[:1000]
        raise HTTPException(status_code=502, detail=f"External AI/OCR API failed: {exc.response.status_code} {body}") from exc
    except Exception as exc:
        judgment.extraction_status = "FLAGGED"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Judgment processing failed: {exc}") from exc

    judgment.case_number = extraction.case_number
    judgment.date_of_order = extraction.date_of_order
    judgment.ocr_used = ocr_used
    judgment.overall_confidence = confidence
    judgment.extraction_status = "FLAGGED" if confidence < settings.ocr_confidence_threshold else "EXTRACTED"

    for field_name, value in extraction.model_dump(mode="json").items():
        if field_name in {"coordinate_map", "confidence_scores"}:
            continue
        meta = field_meta.get(field_name, {"score": 0.0, "source": "LLM", "conflict": False})
        coords = extraction.coordinate_map.get(field_name, [])
        first = coords[0].model_dump() if coords else None
        db.add(
            Extraction(
                judgment_id=judgment.id,
                field_name=field_name,
                extracted_value=_serializable(value),
                confidence_score=meta["score"],
                source_page=first["page"] if first else None,
                source_bbox=first["bbox"] if first else None,
                extraction_source=meta["source"],
                conflict=meta["conflict"],
            )
        )

    for item in action_items:
        db.add(
            ActionPlan(
                judgment_id=judgment.id,
                directive_type=item.directive_type,
                recommended_action=item.recommended_action,
                responsible_authority=item.responsible_authority,
                deadline_date=item.deadline_date,
                priority_level=item.priority_level,
                action_notes=item.notes,
            )
        )
    db.commit()
    return UploadResponse(
        job_id=judgment.id,
        extraction_status=judgment.extraction_status,
        overall_confidence=judgment.overall_confidence,
        ocr_used=judgment.ocr_used,
    )


@router.get("/{job_id}/review", response_model=ReviewResponse)
def review_judgment(job_id: int, db: Session = Depends(get_db)) -> ReviewResponse:
    judgment = db.get(Judgment, job_id)
    if not judgment:
        raise HTTPException(status_code=404, detail="Judgment not found.")
    decisions = {
        row.extraction_id: row.decision
        for row in db.scalars(select(Verification).join(Extraction, Verification.extraction_id == Extraction.id).where(Extraction.judgment_id == job_id))
    }
    fields = [
        ReviewField(
            id=item.id,
            field_name=item.field_name,
            extracted_value=item.extracted_value,
            confidence_score=item.confidence_score,
            source_page=item.source_page,
            source_bbox=item.source_bbox,
            extraction_source=item.extraction_source,
            conflict=item.conflict,
            decision=decisions.get(item.id),
        )
        for item in db.scalars(select(Extraction).where(Extraction.judgment_id == job_id)).all()
    ]
    action_plan = [
        ActionPlanItem(
            directive_type=item.directive_type,
            recommended_action=item.recommended_action,
            responsible_authority=item.responsible_authority,
            deadline_date=item.deadline_date,
            priority_level=item.priority_level,
            notes=item.action_notes,
        )
        for item in db.scalars(select(ActionPlan).where(ActionPlan.judgment_id == job_id)).all()
    ]
    return ReviewResponse(
        job_id=judgment.id,
        pdf_url=f"/storage/pdfs/{Path(judgment.pdf_path).name}",
        extraction_status=judgment.extraction_status,
        overall_confidence=judgment.overall_confidence,
        fields=fields,
        action_plan=action_plan,
    )


@router.patch("/{job_id}/fields/{field_id}", response_model=FieldDecisionResponse)
def decide_field(job_id: int, field_id: int, payload: FieldDecisionRequest, db: Session = Depends(get_db)) -> FieldDecisionResponse:
    field = db.get(Extraction, field_id)
    if not field or field.judgment_id != job_id:
        raise HTTPException(status_code=404, detail="Field not found for this judgment.")
    if payload.decision == "REJECTED" and not payload.rejection_reason:
        raise HTTPException(status_code=400, detail="Rejecting a field requires a reason.")
    if payload.decision == "EDITED" and payload.corrected_value is None:
        raise HTTPException(status_code=400, detail="Editing a field requires corrected_value.")

    existing = db.scalar(select(Verification).where(Verification.extraction_id == field.id))
    verification = existing or Verification(extraction_id=field.id)
    verification.decision = payload.decision
    verification.original_value = field.extracted_value
    verification.corrected_value = payload.corrected_value
    verification.rejection_reason = payload.rejection_reason
    db.add(verification)
    db.commit()
    db.refresh(verification)
    return FieldDecisionResponse(extraction_id=field.id, decision=verification.decision, reviewed_at=verification.reviewed_at)


@router.post("/{job_id}/verify", response_model=VerifyResponse)
async def verify_judgment(
    job_id: int,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> VerifyResponse:
    judgment = db.get(Judgment, job_id)
    if not judgment:
        raise HTTPException(status_code=404, detail="Judgment not found.")
    fields = db.scalars(select(Extraction).where(Extraction.judgment_id == job_id)).all()
    decisions = {
        row.extraction_id: row
        for row in db.scalars(select(Verification).join(Extraction, Verification.extraction_id == Extraction.id).where(Extraction.judgment_id == job_id))
    }
    missing = [field.field_name for field in fields if field.id not in decisions]
    if missing:
        raise HTTPException(status_code=409, detail={"message": "All fields must be reviewed before final verification.", "missing": missing})

    action_items = db.scalars(select(ActionPlan).where(ActionPlan.judgment_id == job_id)).all()
    summary_en = " | ".join(f"{item.directive_type}: {item.recommended_action}" for item in action_items)
    summary_kn = await SarvamClient(settings).translate_to_kannada(summary_en) if summary_en else ""
    values = {field.field_name: decisions[field.id].corrected_value if decisions[field.id].decision == "EDITED" else field.extracted_value for field in fields}
    audit = [
        {
            "field_name": field.field_name,
            "decision": decisions[field.id].decision,
            "original_value": decisions[field.id].original_value,
            "corrected_value": decisions[field.id].corrected_value,
            "rejection_reason": decisions[field.id].rejection_reason,
            "reviewed_at": decisions[field.id].reviewed_at.isoformat(),
        }
        for field in fields
    ]
    first_action = action_items[0] if action_items else None
    record = VerifiedRecord(
        judgment_id=judgment.id,
        case_number=values.get("case_number"),
        department=values.get("responsible_department"),
        urgency_band=values.get("urgency_band") or (first_action.priority_level if first_action else "GREEN"),
        appeal_deadline=_as_date(values.get("appeal_deadline_date")),
        action_summary_en=summary_en,
        action_summary_kn=summary_kn,
        audit_trail=audit,
    )
    for item in action_items:
        item.status = "VERIFIED"
    judgment.extraction_status = "VERIFIED"
    db.add(record)
    db.commit()
    db.refresh(record)
    return VerifyResponse(job_id=judgment.id, status=judgment.extraction_status, verified_record_id=record.id)
