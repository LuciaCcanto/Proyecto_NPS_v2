import enum
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserRole(str, enum.Enum):
    SUPERADMIN = "superadmin"
    MASTER = "master"
    COMPANY_ADMIN = "company_admin"
    BRANCH_OPERATOR = "branch_operator"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(512), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default=UserRole.BRANCH_OPERATOR.value)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    company_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("companies.id"), nullable=True)
    branch_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("branches.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    company: Mapped[Optional["Company"]] = relationship("Company", back_populates="users", foreign_keys=[company_id])  # noqa
    branch: Mapped[Optional["Branch"]] = relationship("Branch", back_populates="users", foreign_keys=[branch_id])  # noqa
    tickets_assigned: Mapped[List["Ticket"]] = relationship("Ticket", back_populates="assigned_to")  # noqa
