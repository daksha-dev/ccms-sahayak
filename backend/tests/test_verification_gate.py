from datetime import date

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.judgments import verify_judgment
from app.core.database import Base
from app.core.config import Settings
from app.models.entities import ActionPlan, Extraction, Judgment


@pytest.fixture()
def db() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


@pytest.mark.asyncio
async def test_verify_requires_every_field_reviewed(db: Session) -> None:
    judgment = Judgment(pdf_path="sample.pdf", extraction_status="EXTRACTED", overall_confidence=0.9)
    db.add(judgment)
    db.commit()
    db.refresh(judgment)
    db.add_all(
        [
            Extraction(judgment_id=judgment.id, field_name="case_number", extracted_value="WP No. 1 of 2026", confidence_score=0.9),
            Extraction(judgment_id=judgment.id, field_name="urgency_band", extracted_value="RED", confidence_score=0.9),
            ActionPlan(
                judgment_id=judgment.id,
                directive_type="COMPLIANCE",
                recommended_action="Comply with the order",
                responsible_authority="Department Secretary",
                deadline_date=date(2026, 5, 8),
                priority_level="RED",
            ),
        ]
    )
    db.commit()

    with pytest.raises(HTTPException) as exc:
        await verify_judgment(judgment.id, db=db, settings=Settings(sarvam_api_key="missing-for-test"))

    assert exc.value.status_code == 409


def test_dashboard_is_backed_by_verified_records_only() -> None:
    from app.api.dashboard import stats

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Judgment(pdf_path="unverified.pdf", extraction_status="EXTRACTED", overall_confidence=0.9))
    session.commit()
    result = stats(db=session)
    assert result.total_active_cases == 0
