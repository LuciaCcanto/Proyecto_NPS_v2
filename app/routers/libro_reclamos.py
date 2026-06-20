import secrets
import string
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_from_cookie, generate_csrf_token, validate_csrf_token
from app.models.checklist import LibroReclamos

router = APIRouter(prefix="/reclamos", tags=["libro_reclamos"])
templates = Jinja2Templates(directory="templates")


def _generate_tracking_id() -> str:
    chars = string.ascii_uppercase + string.digits
    suffix = "".join(secrets.choice(chars) for _ in range(8))
    year = datetime.now(timezone.utc).strftime("%Y")
    return f"REC-{year}-{suffix}"


@router.get("/nuevo", response_class=HTMLResponse)
async def new_reclamo_form(
    request: Request,
    response_id: Optional[int] = None,
    company_id: Optional[int] = None,
    branch_id: Optional[int] = None,
    survey_slug: Optional[str] = None,
):
    # If already submitted, redirect away from the form
    tracking_done = request.cookies.get("reclamo_done")
    if tracking_done:
        slug_cookie = request.cookies.get("reclamo_survey_slug")
        if slug_cookie:
            return RedirectResponse(url=f"/survey/{slug_cookie}/thank-you", status_code=303)
        return RedirectResponse(url=f"/reclamos/confirmacion/{tracking_done}", status_code=303)

    csrf_token = generate_csrf_token()
    resp = templates.TemplateResponse("libro_reclamos.html", {
        "request": request,
        "csrf_token": csrf_token,
        "response_id": response_id,
        "company_id": company_id,
        "branch_id": branch_id,
        "survey_slug": survey_slug,
        "mode": "create",
    })
    resp.set_cookie("csrf_token", csrf_token, httponly=True, samesite="strict")
    if survey_slug:
        resp.set_cookie("reclamo_survey_slug", survey_slug, httponly=True, samesite="strict", max_age=3600)
    return resp


@router.post("/nuevo")
async def submit_reclamo(
    request: Request,
    customer_name: str = Form(...),
    customer_email: str = Form(...),
    customer_dni: Optional[str] = Form(None),
    customer_phone: Optional[str] = Form(None),
    claim_type: str = Form(...),
    description: str = Form(...),
    good_or_service: Optional[str] = Form(None),
    amount_involved: Optional[float] = Form(None),
    csrf_token: str = Form(...),
    company_id: Optional[int] = Form(None),
    branch_id: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    cookie_csrf = request.cookies.get("csrf_token", "")
    if not validate_csrf_token(csrf_token) or csrf_token != cookie_csrf:
        raise HTTPException(status_code=403, detail="CSRF inválido")

    if not company_id:
        company_id = 1

    reclamo = LibroReclamos(
        tracking_id=_generate_tracking_id(),
        company_id=company_id,
        branch_id=branch_id,
        customer_name=customer_name[:255],
        customer_dni=customer_dni[:20] if customer_dni else None,
        customer_email=customer_email[:255].lower().strip(),
        customer_phone=customer_phone[:50] if customer_phone else None,
        claim_type=claim_type[:50],
        description=description[:5000],
        good_or_service=good_or_service if good_or_service in ("bien", "servicio") else None,
        amount_involved=amount_involved,
    )
    db.add(reclamo)
    await db.commit()
    await db.refresh(reclamo)

    redirect = RedirectResponse(url=f"/reclamos/confirmacion/{reclamo.tracking_id}", status_code=303)
    redirect.set_cookie("reclamo_done", reclamo.tracking_id, httponly=True, samesite="strict", max_age=3600)
    return redirect


@router.get("/confirmacion/{tracking_id}", response_class=HTMLResponse)
async def reclamo_confirmation(request: Request, tracking_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(LibroReclamos).where(LibroReclamos.tracking_id == tracking_id)
    result = await db.execute(stmt)
    reclamo = result.scalar_one_or_none()
    if not reclamo:
        raise HTTPException(status_code=404, detail="Reclamo no encontrado")

    survey_slug = request.cookies.get("reclamo_survey_slug")
    thank_you_url = f"/survey/{survey_slug}/thank-you" if survey_slug else "/reclamos"

    return templates.TemplateResponse("libro_reclamos.html", {
        "request": request,
        "reclamo": reclamo,
        "mode": "confirmation",
        "thank_you_url": thank_you_url,
    })


@router.get("", response_class=HTMLResponse)
async def reclamos_list(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        user = get_current_user_from_cookie(request)
    except Exception:
        return RedirectResponse(url="/login")

    company_id = user.get("company_id")
    stmt = (
        select(LibroReclamos)
        .where(LibroReclamos.company_id == company_id)
        .order_by(LibroReclamos.created_at.desc())
        .limit(100)
    )
    result = await db.execute(stmt)
    reclamos = result.scalars().all()

    return templates.TemplateResponse("libro_reclamos.html", {
        "request": request,
        "user": user,
        "reclamos": reclamos,
        "mode": "list",
    })
