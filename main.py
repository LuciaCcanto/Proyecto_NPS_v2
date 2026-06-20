import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.core.config import get_settings
from app.core.database import create_all_tables
from app.routers import auth, dashboard, ingestion, tickets, libro_reclamos, checklist, notifications, users

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando 360° NPS Platform...")
    await create_all_tables()
    await _seed_demo_data()
    yield
    logger.info("Cerrando plataforma...")


async def _seed_demo_data():
    from app.core.database import AsyncSessionLocal
    from app.core.security import hash_password
    from app.models.user import User, UserRole
    from app.models.company import Company, Branch
    from app.models.survey import Survey, SurveyType, ChannelType, Question, QuestionType
    from sqlalchemy import select
    import secrets

    async with AsyncSessionLocal() as db:
        stmt = select(Company).limit(1)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            return

        company = Company(
            name="Empresa Demo S.A.",
            slug="demo",
            industry="Retail",
            google_review_url=settings.GOOGLE_REVIEW_URL,
            trustpilot_url=settings.TRUSTPILOT_URL,
        )
        db.add(company)
        await db.flush()

        branch = Branch(
            company_id=company.id,
            name="Sucursal Principal",
            location="Lima, Perú",
            qr_token=secrets.token_urlsafe(16),
        )
        db.add(branch)
        await db.flush()

        admin = User(
            email="admin@demo.com",
            hashed_password=hash_password("Admin123!"),
            full_name="Administrador Demo",
            role=UserRole.COMPANY_ADMIN,
            company_id=company.id,
        )
        master = User(
            email="master@demo.com",
            hashed_password=hash_password("Master123!"),
            full_name="Master Demo",
            role=UserRole.MASTER,
            company_id=company.id,
        )
        db.add(admin)
        db.add(master)

        survey = Survey(
            company_id=company.id,
            branch_id=branch.id,
            name="Encuesta NPS Principal",
            survey_type=SurveyType.NPS,
            channel=ChannelType.WEB,
            slug="encuesta-demo",
            welcome_message="¡Gracias por visitarnos! Tu opinión nos ayuda a mejorar.",
            thank_you_message="¡Gracias por tu feedback! Lo tomamos muy en cuenta.",
        )
        db.add(survey)
        await db.flush()

        q1 = Question(
            survey_id=survey.id,
            text="¿Qué tan probable es que nos recomiendes a un amigo o familiar?",
            question_type=QuestionType.NPS_SCALE,
            order=1,
            min_label="Muy improbable",
            max_label="Muy probable",
            scale_min=0,
            scale_max=10,
        )
        q2 = Question(
            survey_id=survey.id,
            text="¿Hay algo específico que podríamos mejorar?",
            question_type=QuestionType.TEXT,
            order=2,
            is_required=False,
        )
        db.add(q1)
        db.add(q2)
        await db.commit()
        logger.info("Datos de demo creados. admin@demo.com/Admin123! · master@demo.com/Master123!")


app = FastAPI(
    title=settings.APP_NAME,
    description="Plataforma 360° de Feedback y Medición de Satisfacción del Cliente",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.APP_DEBUG else None,
    redoc_url=None,
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(ingestion.router)
app.include_router(tickets.router)
app.include_router(libro_reclamos.router)
app.include_router(checklist.router)
app.include_router(notifications.router)
app.include_router(users.router)

templates = Jinja2Templates(directory="templates")


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return templates.TemplateResponse("404.html", {"request": request}, status_code=404)


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    logger.error("Error interno: %s", exc)
    return templates.TemplateResponse("error.html", {"request": request}, status_code=500)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.APP_DEBUG,
    )
