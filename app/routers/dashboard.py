import logging
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_from_cookie
from app.services.analytics_service import (
    calculate_nps,
    calculate_csat,
    calculate_ces,
    get_trend_data,
    get_sentiment_distribution,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="templates")

_EMPTY_NPS  = {"nps_score": 0, "total_responses": 0, "promoters": 0, "passives": 0,
               "detractors": 0, "promoters_pct": 0, "passives_pct": 0, "detractors_pct": 0}
_EMPTY_CSAT = {"csat_score": 0, "csat_pct": 0, "total_responses": 0, "satisfied": 0}
_EMPTY_CES  = {"ces_score": 0, "total_responses": 0}


@router.get("/", response_class=HTMLResponse)
async def root():
    return RedirectResponse(url="/dashboard")


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    days: int = 30,
    branch_id: Optional[int] = None,
    tipo_feedback: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    try:
        user = get_current_user_from_cookie(request)
    except Exception:
        return RedirectResponse(url="/login")

    company_id = user.get("company_id")
    if not company_id:
        return RedirectResponse(url="/login")

    # Clamp days to safe range
    days = max(1, min(days, 365))
    if tipo_feedback not in ("bien", "servicio"):
        tipo_feedback = None

    kw = dict(db=db, company_id=company_id, branch_id=branch_id, days=days, tipo_feedback=tipo_feedback)

    try:
        nps_data       = await calculate_nps(**kw)
        csat_data      = await calculate_csat(**kw)
        ces_data       = await calculate_ces(**kw)
        trend_data     = await get_trend_data(**kw)
        sentiment_dist = await get_sentiment_distribution(**kw)
    except Exception:
        logger.exception("Error calculando métricas para company_id=%s", company_id)
        nps_data, csat_data, ces_data = _EMPTY_NPS, _EMPTY_CSAT, _EMPTY_CES
        trend_data, sentiment_dist = [], {"Positivo": 0, "Neutral": 0, "Negativo": 0}

    tipo_label = {"bien": "Bienes", "servicio": "Servicios"}.get(tipo_feedback, "Todo")

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "days": days,
        "selected_branch": branch_id,
        "tipo_feedback": tipo_feedback,
        "tipo_label": tipo_label,
        "nps": nps_data,
        "csat": csat_data,
        "ces": ces_data,
        "trend_labels": [d["date"] for d in trend_data],
        "trend_nps":    [d["nps"]   for d in trend_data],
        "trend_total":  [d["total"] for d in trend_data],
        "sentiment_dist": sentiment_dist,
    })


@router.get("/encuesta-demo", response_class=HTMLResponse)
async def encuesta_demo_page(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        user = get_current_user_from_cookie(request)
    except Exception:
        return RedirectResponse(url="/login")

    from app.models.survey import Survey
    stmt = select(Survey).where(Survey.slug == "encuesta-demo")
    survey = (await db.execute(stmt)).scalar_one_or_none()

    base_url = str(request.base_url).rstrip("/")
    survey_url = f"{base_url}/survey/encuesta-demo"
    preview_url = f"{base_url}/survey/encuesta-demo?mode=master"

    return templates.TemplateResponse("encuesta_demo.html", {
        "request": request,
        "user": user,
        "survey": survey,
        "survey_url": survey_url,
        "preview_url": preview_url,
    })
