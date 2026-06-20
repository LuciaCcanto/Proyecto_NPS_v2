from typing import Optional
from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.response import Response, SentimentType
from app.models.survey import Survey


def _base_filters(company_id: int, days: int, branch_id=None, tipo_feedback=None, cutoff=None):
    from datetime import datetime, timedelta, timezone
    if cutoff is None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    filters = [
        Response.company_id == company_id,
        Response.created_at >= cutoff,
    ]
    if branch_id:
        filters.append(Response.branch_id == branch_id)
    if tipo_feedback and tipo_feedback in ("bien", "servicio"):
        filters.append(Response.tipo_feedback == tipo_feedback)
    return filters


async def calculate_nps(
    db: AsyncSession,
    company_id: int,
    branch_id: Optional[int] = None,
    survey_id: Optional[int] = None,
    days: int = 30,
    tipo_feedback: Optional[str] = None,
) -> dict:
    filters = _base_filters(company_id, days, branch_id, tipo_feedback)
    filters.append(Response.nps_score.is_not(None))
    if survey_id:
        filters.append(Response.survey_id == survey_id)

    stmt = select(
        func.count(Response.id).label("total"),
        func.sum(case((Response.nps_score >= 9, 1), else_=0)).label("promoters"),
        func.sum(case((Response.nps_score <= 6, 1), else_=0)).label("detractors"),
        func.sum(case((and_(Response.nps_score >= 7, Response.nps_score <= 8), 1), else_=0)).label("passives"),
    ).where(and_(*filters))

    result = (await db.execute(stmt)).one()
    total = result.total or 0
    promoters = result.promoters or 0
    detractors = result.detractors or 0
    passives = result.passives or 0

    nps_score = round(((promoters - detractors) / total) * 100, 1) if total else 0.0

    return {
        "nps_score": nps_score,
        "total_responses": total,
        "promoters": promoters,
        "passives": passives,
        "detractors": detractors,
        "promoters_pct": round((promoters / total * 100) if total else 0, 1),
        "passives_pct": round((passives / total * 100) if total else 0, 1),
        "detractors_pct": round((detractors / total * 100) if total else 0, 1),
    }


async def calculate_csat(
    db: AsyncSession,
    company_id: int,
    branch_id: Optional[int] = None,
    days: int = 30,
    tipo_feedback: Optional[str] = None,
) -> dict:
    filters = _base_filters(company_id, days, branch_id, tipo_feedback)
    filters.append(Response.csat_score.is_not(None))

    stmt = select(
        func.count(Response.id).label("total"),
        func.avg(Response.csat_score).label("avg_score"),
        func.sum(case((Response.csat_score >= 4, 1), else_=0)).label("satisfied"),
    ).where(and_(*filters))

    result = (await db.execute(stmt)).one()
    total = result.total or 0
    avg_score = round(float(result.avg_score or 0), 2)
    satisfied = result.satisfied or 0

    return {
        "csat_score": avg_score,
        "csat_pct": round((satisfied / total * 100) if total else 0, 1),
        "total_responses": total,
        "satisfied": satisfied,
    }


async def calculate_ces(
    db: AsyncSession,
    company_id: int,
    branch_id: Optional[int] = None,
    days: int = 30,
    tipo_feedback: Optional[str] = None,
) -> dict:
    filters = _base_filters(company_id, days, branch_id, tipo_feedback)
    filters.append(Response.ces_score.is_not(None))

    stmt = select(
        func.count(Response.id).label("total"),
        func.avg(Response.ces_score).label("avg_ces"),
    ).where(and_(*filters))

    result = (await db.execute(stmt)).one()
    total = result.total or 0

    return {
        "ces_score": round(float(result.avg_ces or 0), 2),
        "total_responses": total,
    }


async def get_trend_data(
    db: AsyncSession,
    company_id: int,
    branch_id: Optional[int] = None,
    days: int = 30,
    tipo_feedback: Optional[str] = None,
) -> list[dict]:
    filters = _base_filters(company_id, days, branch_id, tipo_feedback)
    filters.append(Response.nps_score.is_not(None))

    date_col = func.date(Response.created_at).label("date")
    stmt = (
        select(
            date_col,
            func.count(Response.id).label("total"),
            func.sum(case((Response.nps_score >= 9, 1), else_=0)).label("promoters"),
            func.sum(case((Response.nps_score <= 6, 1), else_=0)).label("detractors"),
        )
        .where(and_(*filters))
        .group_by(func.date(Response.created_at))
        .order_by(func.date(Response.created_at))
    )

    rows = (await db.execute(stmt)).mappings().all()
    result = []
    for row in rows:
        total = row["total"] or 0
        promoters = row["promoters"] or 0
        detractors = row["detractors"] or 0
        nps = round(((promoters - detractors) / total) * 100, 1) if total else 0
        result.append({"date": str(row["date"]), "nps": nps, "total": total})
    return result


async def get_sentiment_distribution(
    db: AsyncSession,
    company_id: int,
    branch_id: Optional[int] = None,
    days: int = 30,
    tipo_feedback: Optional[str] = None,
) -> dict:
    filters = _base_filters(company_id, days, branch_id, tipo_feedback)
    filters.append(Response.ai_processed == True)  # noqa: E712

    stmt = select(
        Response.sentiment,
        func.count(Response.id).label("count"),
    ).where(and_(*filters)).group_by(Response.sentiment)

    rows = (await db.execute(stmt)).all()
    distribution = {"Positivo": 0, "Neutral": 0, "Negativo": 0}
    for row in rows:
        if row.sentiment and row.sentiment in distribution:
            distribution[row.sentiment] = row.count
    return distribution
