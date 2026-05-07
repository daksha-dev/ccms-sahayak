from datetime import date

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.entities import VerifiedRecord
from app.schemas.dto import DashboardRecord, DashboardResponse, DashboardStats

router = APIRouter()


def _query(db: Session, department: str | None, action_type: str | None, urgency: str | None):
    query = select(VerifiedRecord)
    if department:
        departments = [item.strip() for item in department.split(",") if item.strip()]
        query = query.where(VerifiedRecord.department.in_(departments))
    if urgency:
        query = query.where(VerifiedRecord.urgency_band == urgency)
    if action_type:
        query = query.where(
            or_(
                VerifiedRecord.action_summary_en.ilike(f"%{action_type}%"),
                VerifiedRecord.action_summary_kn.ilike(f"%{action_type}%"),
            )
        )
    return query.order_by(VerifiedRecord.verified_at.desc())


@router.get("", response_model=DashboardResponse)
def dashboard(
    department: str | None = None,
    action_type: str | None = None,
    urgency: str | None = None,
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db),
) -> DashboardResponse:
    query = _query(db, department, action_type, urgency)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.offset((page - 1) * limit).limit(limit)).all()
    return DashboardResponse(
        records=[DashboardRecord.model_validate(row, from_attributes=True) for row in rows],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/stats", response_model=DashboardStats)
def stats(db: Session = Depends(get_db)) -> DashboardStats:
    rows = db.scalars(select(VerifiedRecord)).all()
    today = date.today()
    return DashboardStats(
        total_active_cases=len(rows),
        red_urgency=sum(1 for row in rows if row.urgency_band == "RED"),
        amber_urgency=sum(1 for row in rows if row.urgency_band == "AMBER"),
        pending_appeals=sum(1 for row in rows if row.appeal_deadline and row.appeal_deadline >= today),
    )


@router.get("/export.csv")
def export_csv(
    department: str | None = None,
    action_type: str | None = None,
    urgency: str | None = None,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    rows = db.scalars(_query(db, department, action_type, urgency)).all()

    def body():
        yield "case_number,department,urgency_band,appeal_deadline,action_summary_en,action_summary_kn\n"
        for row in rows:
            values = [
                row.case_number or "",
                row.department or "",
                row.urgency_band,
                row.appeal_deadline.isoformat() if row.appeal_deadline else "",
                (row.action_summary_en or "").replace('"', '""'),
                (row.action_summary_kn or "").replace('"', '""'),
            ]
            yield ",".join(f'"{value}"' for value in values) + "\n"

    return StreamingResponse(body(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=ccms_sahayak_dashboard.csv"})
