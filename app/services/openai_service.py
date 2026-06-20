import json
import logging
from typing import Optional

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import get_settings
from app.models.response import Response, SentimentType
from app.models.company import AIConfig

settings = get_settings()
logger = logging.getLogger(__name__)

_client: Optional[AsyncOpenAI] = None


def get_openai_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


DEFAULT_SYSTEM_PROMPT = (
    "Eres un analista experto en experiencia del cliente. Analiza el comentario y devuelve "
    "ÚNICAMENTE un objeto JSON válido con los siguientes campos:\n"
    "- sentiment: 'Positivo', 'Neutral', o 'Negativo'\n"
    "- emotion: 'Satisfacción', 'Frustración', 'Alegría', 'Enojo', 'Indiferencia', u otra emoción relevante\n"
    "- category: área principal como 'Atención al Cliente', 'Producto', 'Precio', "
    "'Tiempo de Espera', 'Instalaciones', 'Proceso', u otra\n"
    "- sub_category: detalle específico dentro de la categoría\n"
    "- key_phrase: la frase más relevante extraída del comentario (máx 50 caracteres)\n"
    "No incluyas texto adicional fuera del JSON."
)


async def get_company_prompt(db: AsyncSession, company_id: int) -> str:
    stmt = select(AIConfig).where(AIConfig.company_id == company_id)
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()
    return config.system_prompt if config else DEFAULT_SYSTEM_PROMPT


async def analyze_comment(
    db: AsyncSession,
    response_id: int,
    comment: str,
    company_id: int,
) -> bool:
    if not comment or not comment.strip():
        return False
    if not settings.OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY no configurado, omitiendo análisis de IA")
        return False

    try:
        system_prompt = await get_company_prompt(db, company_id)
        client = get_openai_client()

        completion = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            max_tokens=settings.OPENAI_MAX_TOKENS,
            temperature=0.1,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Comentario del cliente: {comment}"},
            ],
        )

        raw = completion.choices[0].message.content
        data = json.loads(raw)

        sentiment_map = {
            "positivo": SentimentType.POSITIVE,
            "neutral": SentimentType.NEUTRAL,
            "negativo": SentimentType.NEGATIVE,
        }
        sentiment_raw = str(data.get("sentiment", "")).lower()
        sentiment = sentiment_map.get(sentiment_raw, SentimentType.NEUTRAL)

        stmt = select(Response).where(Response.id == response_id)
        result = await db.execute(stmt)
        response = result.scalar_one_or_none()

        if response:
            response.sentiment = sentiment
            response.emotion = str(data.get("emotion", ""))[:100]
            response.category = str(data.get("category", ""))[:100]
            response.sub_category = str(data.get("sub_category", ""))[:100]
            response.key_phrase = str(data.get("key_phrase", ""))[:500]
            response.ai_processed = True
            await db.commit()

        return True

    except Exception as exc:
        logger.error("Error en análisis OpenAI para response %d: %s", response_id, exc)
        return False
