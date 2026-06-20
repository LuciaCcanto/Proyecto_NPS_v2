import enum
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import String, Boolean, DateTime, Enum, ForeignKey, Integer, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SurveyType(str, enum.Enum):
    NPS = "nps"
    CSAT = "csat"
    CES = "ces"
    MIXED = "mixed"


class QuestionType(str, enum.Enum):
    NPS_SCALE = "nps_scale"
    RATING_SCALE = "rating_scale"
    TEXT = "text"
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"


class ChannelType(str, enum.Enum):
    WEB = "web"
    QR = "qr"
    TABLET = "tablet"
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    POS = "pos"
    API = "api"


class Survey(Base):
    __tablename__ = "surveys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id"), nullable=False)
    branch_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("branches.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    survey_type: Mapped[SurveyType] = mapped_column(Enum(SurveyType), nullable=False, default=SurveyType.NPS)
    channel: Mapped[ChannelType] = mapped_column(Enum(ChannelType), nullable=False, default=ChannelType.WEB)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    welcome_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    thank_you_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    company: Mapped["Company"] = relationship("Company", back_populates="surveys")  # noqa
    branch: Mapped[Optional["Branch"]] = relationship("Branch", back_populates="surveys")  # noqa
    questions: Mapped[List["Question"]] = relationship("Question", back_populates="survey", cascade="all, delete-orphan", order_by="Question.order")
    responses: Mapped[List["Response"]] = relationship("Response", back_populates="survey")  # noqa


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    survey_id: Mapped[int] = mapped_column(Integer, ForeignKey("surveys.id"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[QuestionType] = mapped_column(Enum(QuestionType), nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    min_label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    max_label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    scale_min: Mapped[int] = mapped_column(Integer, default=0)
    scale_max: Mapped[int] = mapped_column(Integer, default=10)

    survey: Mapped["Survey"] = relationship("Survey", back_populates="questions")
    options: Mapped[List["QuestionOption"]] = relationship("QuestionOption", back_populates="question", cascade="all, delete-orphan")
    answers: Mapped[List["ResponseAnswer"]] = relationship("ResponseAnswer", back_populates="question")  # noqa


class QuestionOption(Base):
    __tablename__ = "question_options"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("questions.id"), nullable=False)
    text: Mapped[str] = mapped_column(String(255), nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0)

    question: Mapped["Question"] = relationship("Question", back_populates="options")
