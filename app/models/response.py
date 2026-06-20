import enum
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import String, DateTime, Enum, ForeignKey, Integer, Text, Float, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SentimentType(str, enum.Enum):
    POSITIVE = "Positivo"
    NEUTRAL = "Neutral"
    NEGATIVE = "Negativo"
    PENDING = "Pendiente"


class Response(Base):
    __tablename__ = "responses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    survey_id: Mapped[int] = mapped_column(Integer, ForeignKey("surveys.id"), nullable=False)
    branch_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("branches.id"), nullable=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id"), nullable=False)

    # NPS/CSAT/CES core scores
    nps_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    csat_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ces_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    open_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Channel & metadata
    channel: Mapped[str] = mapped_column(String(50), nullable=False, default="web")
    tipo_feedback: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # "bien" | "servicio"
    customer_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    customer_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)

    # AI Analysis results
    sentiment: Mapped[SentimentType] = mapped_column(Enum(SentimentType), default=SentimentType.PENDING)
    emotion: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sub_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    key_phrase: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_processed: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    survey: Mapped["Survey"] = relationship("Survey", back_populates="responses")  # noqa
    answers: Mapped[List["ResponseAnswer"]] = relationship("ResponseAnswer", back_populates="response", cascade="all, delete-orphan")
    ticket: Mapped[Optional["Ticket"]] = relationship("Ticket", back_populates="response", uselist=False)  # noqa


class ResponseAnswer(Base):
    __tablename__ = "response_answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    response_id: Mapped[int] = mapped_column(Integer, ForeignKey("responses.id"), nullable=False)
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("questions.id"), nullable=False)
    numeric_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    text_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    selected_options: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    response: Mapped["Response"] = relationship("Response", back_populates="answers")
    question: Mapped["Question"] = relationship("Question", back_populates="answers")  # noqa
