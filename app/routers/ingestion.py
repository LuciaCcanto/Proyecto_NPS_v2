import hmac
import hashlib
import secrets
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.models.response import Response
from app.models.survey import Survey, ChannelType
from app.services.openai_service import analyze_comment
from app.services.workflow_engine import evaluate_rules

settings = get_settings()
router = APIRouter(prefix="/survey", tags=["ingestion"])
templates = Jinja2Templates(directory="templates")


async def _get_survey_by_slug(slug: str, db: AsyncSession) -> Survey:
    from app.models.survey import Question, QuestionOption
    stmt = (
        select(Survey)
        .options(
            selectinload(Survey.questions).selectinload(Question.options),
            selectinload(Survey.branch),
        )
        .where(Survey.slug == slug, Survey.is_active == True)  # noqa: E712
    )
    result = await db.execute(stmt)
    survey = result.scalar_one_or_none()
    if not survey:
        raise HTTPException(status_code=404, detail="Encuesta no encontrada")
    return survey


async def _process_response_background(response_id: int, comment: str, company_id: int):
    import logging
    _log = logging.getLogger(__name__)
    try:
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            await analyze_comment(db, response_id, comment, company_id)
            stmt = select(Response).where(Response.id == response_id)
            resp_obj = (await db.execute(stmt)).scalar_one_or_none()
            if resp_obj:
                await evaluate_rules(db, resp_obj)
    except Exception:
        _log.exception("Error en background task para response_id=%s", response_id)


@router.get("/{slug}/already-done", response_class=HTMLResponse)
async def already_done_page(request: Request, slug: str):
    return templates.TemplateResponse("already_submitted.html", {
        "request": request,
        "slug": slug,
    })


def _is_master_mode(request: Request) -> bool:
    if request.query_params.get("mode") == "master":
        return True
    try:
        from app.core.security import get_current_user_from_cookie
        u = get_current_user_from_cookie(request)
        return u.get("role") in ("master", "superadmin")
    except Exception:
        return False


@router.get("/{slug}", response_class=HTMLResponse)
async def survey_page(
    request: Request,
    slug: str,
    db: AsyncSession = Depends(get_db),
    channel: str = "web",
):
    if request.cookies.get(f"sdone_{slug}") and not _is_master_mode(request):
        return templates.TemplateResponse("already_submitted.html", {
            "request": request,
            "slug": slug,
        })

    survey = await _get_survey_by_slug(slug, db)
    from app.core.security import generate_csrf_token
    csrf_token = generate_csrf_token()
    resp = templates.TemplateResponse("survey.html", {
        "request": request,
        "survey": survey,
        "csrf_token": csrf_token,
        "channel": channel,
    })
    resp.set_cookie("csrf_token", csrf_token, httponly=True, samesite="strict")
    return resp


@router.post("/{slug}/submit")
async def submit_survey(
    request: Request,
    slug: str,
    background_tasks: BackgroundTasks,
    nps_score: Optional[int] = Form(None),
    csat_score: Optional[float] = Form(None),
    ces_score: Optional[float] = Form(None),
    open_comment: Optional[str] = Form(None),
    customer_email: Optional[str] = Form(None),
    customer_phone: Optional[str] = Form(None),
    tipo_feedback: Optional[str] = Form(None),
    channel: str = Form("web"),
    csrf_token: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    from app.core.security import validate_csrf_token
    cookie_csrf = request.cookies.get("csrf_token", "")
    if not validate_csrf_token(csrf_token) or csrf_token != cookie_csrf:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF inválido")

    master_mode = _is_master_mode(request)

    # Block duplicate submissions (skip for master/superadmin)
    if request.cookies.get(f"sdone_{slug}") and not master_mode:
        return RedirectResponse(url=f"/survey/{slug}/already-done", status_code=303)

    survey = await _get_survey_by_slug(slug, db)
    client_ip = request.client.host if request.client else None

    if open_comment:
        open_comment = open_comment[:2000]
    if customer_email:
        customer_email = customer_email[:255].lower().strip()
    if tipo_feedback not in ("bien", "servicio"):
        tipo_feedback = None

    response = Response(
        survey_id=survey.id,
        company_id=survey.company_id,
        branch_id=survey.branch_id,
        nps_score=nps_score,
        csat_score=csat_score,
        ces_score=ces_score,
        open_comment=open_comment,
        customer_email=customer_email,
        customer_phone=customer_phone,
        tipo_feedback=tipo_feedback,
        channel=channel,
        ip_address=client_ip,
    )
    db.add(response)
    await db.flush()
    response_id = response.id
    company_id = survey.company_id
    await db.commit()

    if open_comment and open_comment.strip():
        background_tasks.add_task(
            _process_response_background,
            response_id,
            open_comment,
            company_id,
        )

    if nps_score is not None and nps_score >= 9:
        redirect = RedirectResponse(url=f"/survey/{slug}/promoter", status_code=303)
    elif nps_score is not None and nps_score <= 6:
        redirect = RedirectResponse(
            url=f"/survey/{slug}/reclamo?response_id={response_id}&survey_slug={slug}",
            status_code=303,
        )
    else:
        redirect = RedirectResponse(url=f"/survey/{slug}/thank-you", status_code=303)

    # Only set the done-cookie for regular users (master can re-submit)
    if not master_mode:
        redirect.set_cookie(f"sdone_{slug}", "1", httponly=True, samesite="strict", max_age=86400)
    return redirect


@router.get("/{slug}/promoter", response_class=HTMLResponse)
async def promoter_page(request: Request, slug: str, db: AsyncSession = Depends(get_db)):
    survey = await _get_survey_by_slug(slug, db)
    from app.models.company import Company
    stmt = select(Company).where(Company.id == survey.company_id)
    result = await db.execute(stmt)
    company = result.scalar_one_or_none()
    return templates.TemplateResponse("promoter.html", {
        "request": request,
        "survey": survey,
        "company": company,
        "google_url": (company.google_review_url if company else None) or settings.GOOGLE_REVIEW_URL,
        "trustpilot_url": (company.trustpilot_url if company else None) or settings.TRUSTPILOT_URL,
    })


@router.get("/{slug}/thank-you", response_class=HTMLResponse)
async def thank_you_page(request: Request, slug: str, db: AsyncSession = Depends(get_db)):
    survey = await _get_survey_by_slug(slug, db)
    return templates.TemplateResponse("thank_you.html", {"request": request, "survey": survey})


@router.get("/{slug}/reclamo", response_class=HTMLResponse)
async def reclamo_redirect(request: Request, slug: str, response_id: Optional[int] = None, survey_slug: Optional[str] = None):
    slug_param = survey_slug or slug
    return RedirectResponse(url=f"/reclamos/nuevo?response_id={response_id or ''}&survey_slug={slug_param}")


@router.post("/api/webhook/whatsapp")
async def whatsapp_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    signature = request.headers.get("X-Hub-Signature-256", "")
    body = await request.body()
    expected = "sha256=" + hmac.new(
        settings.WHATSAPP_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Firma inválida")
    return JSONResponse({"status": "received"})
