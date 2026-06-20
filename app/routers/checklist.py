import logging

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_from_cookie
from app.models.checklist import Checklist, ChecklistExecution, ChecklistItemResult, ChecklistStatus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/checklist", tags=["checklist"])
templates = Jinja2Templates(directory="templates")


def _require_auth(request: Request) -> dict:
    try:
        return get_current_user_from_cookie(request)
    except Exception:
        raise HTTPException(status_code=303, headers={"Location": "/login"})


@router.get("", response_class=HTMLResponse)
async def checklist_list(request: Request, db: AsyncSession = Depends(get_db)):
    user = _require_auth(request)
    company_id = user.get("company_id")

    stmt = (
        select(Checklist)
        .options(selectinload(Checklist.items))
        .where(Checklist.company_id == company_id)
        .order_by(Checklist.created_at.desc())
    )
    checklists = (await db.execute(stmt)).scalars().all()

    return templates.TemplateResponse("checklist.html", {
        "request": request,
        "user": user,
        "checklists": checklists,
        "mode": "list",
    })


@router.get("/{checklist_id}/execute", response_class=HTMLResponse)
async def execute_checklist(
    request: Request,
    checklist_id: int,
    db: AsyncSession = Depends(get_db),
):
    user = _require_auth(request)
    company_id = user.get("company_id")

    stmt = (
        select(Checklist)
        .options(selectinload(Checklist.items))
        .where(Checklist.id == checklist_id, Checklist.company_id == company_id)
    )
    checklist = (await db.execute(stmt)).scalar_one_or_none()
    if not checklist:
        raise HTTPException(status_code=404, detail="Checklist no encontrado")

    from app.core.security import generate_csrf_token
    csrf_token = generate_csrf_token()
    resp = templates.TemplateResponse("checklist.html", {
        "request": request,
        "user": user,
        "checklist": checklist,
        "csrf_token": csrf_token,
        "mode": "execute",
    })
    resp.set_cookie("csrf_token", csrf_token, httponly=True, samesite="strict")
    return resp


@router.post("/{checklist_id}/execute")
async def submit_checklist(
    request: Request,
    checklist_id: int,
    notes: str = Form(""),
    csrf_token: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    from app.core.security import validate_csrf_token
    user = _require_auth(request)
    cookie_csrf = request.cookies.get("csrf_token", "")
    if not validate_csrf_token(csrf_token) or csrf_token != cookie_csrf:
        raise HTTPException(status_code=403, detail="CSRF inválido")

    company_id = user.get("company_id")

    # Eagerly load items to avoid lazy-load in async context
    stmt = (
        select(Checklist)
        .options(selectinload(Checklist.items))
        .where(Checklist.id == checklist_id, Checklist.company_id == company_id)
    )
    checklist = (await db.execute(stmt)).scalar_one_or_none()
    if not checklist:
        raise HTTPException(status_code=404)

    form_data = await request.form()
    total_items = len(checklist.items)
    compliant_count = 0
    item_results = []

    for item in checklist.items:
        is_compliant = form_data.get(f"item_{item.id}") == "on"
        if is_compliant:
            compliant_count += 1
        item_results.append((item.id, is_compliant))

    score = round((compliant_count / total_items * 100) if total_items else 0, 1)

    execution = ChecklistExecution(
        checklist_id=checklist_id,
        executed_by_id=int(user["sub"]),
        status=ChecklistStatus.COMPLETED,
        compliance_score=score,
        notes=notes[:1000] if notes else None,
    )
    db.add(execution)
    await db.flush()

    for item_id, is_compliant in item_results:
        db.add(ChecklistItemResult(
            execution_id=execution.id,
            item_id=item_id,
            is_compliant=is_compliant,
        ))

    await db.commit()
    logger.info("Checklist %s ejecutado por user %s — score %.1f%%", checklist_id, user["sub"], score)
    return RedirectResponse(url="/checklist", status_code=303)
