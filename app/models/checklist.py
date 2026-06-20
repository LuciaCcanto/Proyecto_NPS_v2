import enum
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import String, DateTime, Enum, ForeignKey, Integer, Text, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ChecklistStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class Checklist(Base):
    __tablename__ = "checklists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id"), nullable=False)
    branch_id: Mapped[int] = mapped_column(Integer, ForeignKey("branches.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_template: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    items: Mapped[List["ChecklistItem"]] = relationship("ChecklistItem", back_populates="checklist", cascade="all, delete-orphan")
    executions: Mapped[List["ChecklistExecution"]] = relationship("ChecklistExecution", back_populates="checklist")


class ChecklistItem(Base):
    __tablename__ = "checklist_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    checklist_id: Mapped[int] = mapped_column(Integer, ForeignKey("checklists.id"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    order: Mapped[int] = mapped_column(Integer, default=0)
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False)

    checklist: Mapped["Checklist"] = relationship("Checklist", back_populates="items")


class ChecklistExecution(Base):
    __tablename__ = "checklist_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    checklist_id: Mapped[int] = mapped_column(Integer, ForeignKey("checklists.id"), nullable=False)
    executed_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    status: Mapped[ChecklistStatus] = mapped_column(Enum(ChecklistStatus), default=ChecklistStatus.PENDING)
    compliance_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    checklist: Mapped["Checklist"] = relationship("Checklist", back_populates="executions")
    item_results: Mapped[List["ChecklistItemResult"]] = relationship("ChecklistItemResult", back_populates="execution", cascade="all, delete-orphan")


class ChecklistItemResult(Base):
    __tablename__ = "checklist_item_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    execution_id: Mapped[int] = mapped_column(Integer, ForeignKey("checklist_executions.id"), nullable=False)
    item_id: Mapped[int] = mapped_column(Integer, ForeignKey("checklist_items.id"), nullable=False)
    is_compliant: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    execution: Mapped["ChecklistExecution"] = relationship("ChecklistExecution", back_populates="item_results")


class LibroReclamos(Base):
    __tablename__ = "libro_reclamos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tracking_id: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id"), nullable=False)
    branch_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("branches.id"), nullable=True)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_dni: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    customer_email: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    claim_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    good_or_service: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    amount_involved: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    resolution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="received")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
