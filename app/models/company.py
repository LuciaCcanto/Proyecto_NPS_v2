from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import String, Boolean, DateTime, Integer, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    google_review_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    trustpilot_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    branches: Mapped[List["Branch"]] = relationship("Branch", back_populates="company", cascade="all, delete-orphan")
    users: Mapped[List["User"]] = relationship("User", back_populates="company", foreign_keys="User.company_id")  # noqa
    surveys: Mapped[List["Survey"]] = relationship("Survey", back_populates="company")  # noqa
    ai_config: Mapped[Optional["AIConfig"]] = relationship("AIConfig", back_populates="company", uselist=False)  # noqa


class Branch(Base):
    __tablename__ = "branches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    qr_token: Mapped[Optional[str]] = mapped_column(String(64), unique=True, index=True, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    company: Mapped["Company"] = relationship("Company", back_populates="branches")
    users: Mapped[List["User"]] = relationship("User", back_populates="branch", foreign_keys="User.branch_id")  # noqa
    surveys: Mapped[List["Survey"]] = relationship("Survey", back_populates="branch")  # noqa


class AIConfig(Base):
    __tablename__ = "ai_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id"), unique=True, nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False, default=(
        "Eres un analista experto en experiencia del cliente. Analiza el comentario y devuelve "
        "un JSON con: sentiment (Positivo/Neutral/Negativo), emotion (Satisfacción/Frustración/"
        "Alegría/Enojo/Indiferencia), category (área principal: Atención al Cliente, Producto, "
        "Precio, Tiempo de Espera, Instalaciones, Proceso), sub_category (detalle específico), "
        "key_phrase (frase clave extraída del comentario)."
    ))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    company: Mapped["Company"] = relationship("Company", back_populates="ai_config")
