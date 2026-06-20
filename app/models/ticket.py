import enum
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import String, DateTime, Enum, ForeignKey, Integer, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TicketStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticket_number: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id"), nullable=False)
    branch_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("branches.id"), nullable=True)
    response_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("responses.id"), nullable=True)
    assigned_to_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[TicketStatus] = mapped_column(Enum(TicketStatus), default=TicketStatus.OPEN)
    priority: Mapped[TicketPriority] = mapped_column(Enum(TicketPriority), default=TicketPriority.MEDIUM)
    customer_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    customer_contact: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    auto_generated: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    response: Mapped[Optional["Response"]] = relationship("Response", back_populates="ticket")  # noqa
    assigned_to: Mapped[Optional["User"]] = relationship("User", back_populates="tickets_assigned")  # noqa
    audit_logs: Mapped[List["TicketAuditLog"]] = relationship("TicketAuditLog", back_populates="ticket", cascade="all, delete-orphan")


class TicketAuditLog(Base):
    __tablename__ = "ticket_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticket_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickets.id"), nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="audit_logs")
