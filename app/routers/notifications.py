from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.core.security import get_current_user_from_cookie
from app.services.sse_manager import sse_manager

router = APIRouter(prefix="/api", tags=["notifications"])


@router.get("/events")
async def sse_endpoint(request: Request):
    user_data = get_current_user_from_cookie(request)
    company_id = user_data.get("company_id")
    if not company_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Sin empresa asignada")

    async def generate():
        async for chunk in sse_manager.event_generator(int(company_id)):
            if await request.is_disconnected():
                break
            yield chunk

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
