from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_from_cookie
from app.models.ticket import Ticket, TicketStatus, TicketAuditLog
from app.models.user import User

router = APIRouter(prefix="/tickets", tags=["tickets"])
templates = Jinja2Templates(directory="templates")


def _require_auth(request: Request) -> dict:
    try:
        return get_current_user_from_cookie(request)
    except Exception:
        raise HTTPException(status_code=303, headers={"Location": "/login"})


@router.get("", response_class=HTMLResponse)
async def ticket_list(
    request: Request,
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    user = _require_auth(request)
    company_id = user.get("company_id")

    filters = [Ticket.company_id == company_id]
    if status_filter:
        try:
            filters.append(Ticket.status == TicketStatus(status_filter))
        except ValueError:
            pass

    stmt = (
        select(Ticket)
        .where(and_(*filters))
        .order_by(Ticket.created_at.desc())
        .limit(100)
    )
    result = await db.execute(stmt)
    tickets = result.scalars().all()

    return templates.TemplateResponse("tickets.html", {
        "request": request,
        "user": user,
        "tickets": tickets,
        "status_filter": status_filter,
        "TicketStatus": TicketStatus,
    })


@router.get("/{ticket_id}", response_class=HTMLResponse)
async def ticket_detail(
    request: Request,
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
):
    user = _require_auth(request)
    company_id = user.get("company_id")

    stmt = select(Ticket).where(Ticket.id == ticket_id, Ticket.company_id == company_id)
    result = await db.execute(stmt)
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    logs_stmt = (
        select(TicketAuditLog)
        .where(TicketAuditLog.ticket_id == ticket_id)
        .order_by(TicketAuditLog.created_at.desc())
    )
    logs_result = await db.execute(logs_stmt)
    logs = logs_result.scalars().all()

    agents_stmt = select(User).where(User.company_id == company_id, User.is_active == True)  # noqa
    agents_result = await db.execute(agents_stmt)
    agents = agents_result.scalars().all()

    return templates.TemplateResponse("ticket_detail.html", {
        "request": request,
        "user": user,
        "ticket": ticket,
        "logs": logs,
        "agents": agents,
        "TicketStatus": TicketStatus,
    })


@router.post("/{ticket_id}/update")
async def update_ticket(
    request: Request,
    ticket_id: int,
    new_status: str = Form(...),
    resolution_notes: Optional[str] = Form(None),
    assigned_to_id: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    user = _require_auth(request)
    company_id = user.get("company_id")

    stmt = select(Ticket).where(Ticket.id == ticket_id, Ticket.company_id == company_id)
    result = await db.execute(stmt)
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    old_status = ticket.status.value
    try:
        ticket.status = TicketStatus(new_status)
    except ValueError:
        raise HTTPException(status_code=400, detail="Estado inválido")

    if resolution_notes:
        ticket.resolution_notes = resolution_notes[:2000]
    if assigned_to_id:
        ticket.assigned_to_id = assigned_to_id
    if ticket.status == TicketStatus.RESOLVED:
        ticket.resolved_at = datetime.now(timezone.utc)

    log = TicketAuditLog(
        ticket_id=ticket.id,
        user_id=int(user["sub"]),
        action="status_changed",
        details=f"Estado: {old_status} → {new_status}. Notas: {resolution_notes or 'N/A'}",
    )
    db.add(log)
    await db.commit()

    return RedirectResponse(url=f"/tickets/{ticket_id}", status_code=303)
