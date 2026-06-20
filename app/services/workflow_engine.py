import secrets
import string
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.response import Response
from app.models.ticket import Ticket, TicketPriority, TicketStatus, TicketAuditLog
from app.services.sse_manager import sse_manager


def _generate_ticket_number() -> str:
    chars = string.ascii_uppercase + string.digits
    suffix = "".join(secrets.choice(chars) for _ in range(6))
    ts = datetime.now(timezone.utc).strftime("%y%m%d")
    return f"TKT-{ts}-{suffix}"


def _classify_priority(nps_score: int) -> TicketPriority:
    if nps_score <= 3:
        return TicketPriority.CRITICAL
    elif nps_score <= 5:
        return TicketPriority.HIGH
    else:
        return TicketPriority.MEDIUM


async def evaluate_rules(db: AsyncSession, response: Response) -> Ticket | None:
    should_create_ticket = False
    priority = TicketPriority.MEDIUM

    if response.nps_score is not None and response.nps_score <= 6:
        should_create_ticket = True
        priority = _classify_priority(response.nps_score)

    if response.csat_score is not None and response.csat_score <= 2:
        should_create_ticket = True
        if priority != TicketPriority.CRITICAL:
            priority = TicketPriority.HIGH

    if not should_create_ticket:
        return None

    score_desc = f"NPS={response.nps_score}" if response.nps_score is not None else f"CSAT={response.csat_score}"
    ticket = Ticket(
        ticket_number=_generate_ticket_number(),
        company_id=response.company_id,
        branch_id=response.branch_id,
        response_id=response.id,
        title=f"Experiencia negativa detectada ({score_desc})",
        description=(
            f"Se recibió feedback negativo automático.\n"
            f"Puntuación: {score_desc}\n"
            f"Comentario: {response.open_comment or 'Sin comentario'}\n"
            f"Canal: {response.channel}\n"
            f"Contacto: {response.customer_email or response.customer_phone or 'No registrado'}"
        ),
        status=TicketStatus.OPEN,
        priority=priority,
        customer_contact=response.customer_email or response.customer_phone,
        auto_generated=True,
    )
    db.add(ticket)
    await db.flush()

    audit = TicketAuditLog(
        ticket_id=ticket.id,
        action="created",
        details="Ticket generado automáticamente por el motor de reglas",
    )
    db.add(audit)
    await db.commit()

    await sse_manager.broadcast(
        response.company_id,
        "critical_feedback",
        {
            "ticket_number": ticket.ticket_number,
            "score": score_desc,
            "priority": priority.value,
            "branch_id": response.branch_id,
            "message": f"Nuevo ticket crítico: {ticket.title}",
        },
    )

    return ticket


async def generate_qr_token() -> str:
    return secrets.token_urlsafe(32)
