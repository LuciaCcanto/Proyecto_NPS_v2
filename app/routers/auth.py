from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    generate_csrf_token,
    get_current_user_from_cookie,
    hash_password,
    needs_rehash,
    validate_csrf_token,
    verify_password,
)
from app.models.user import User

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    csrf_token = generate_csrf_token()
    response = templates.TemplateResponse("login.html", {"request": request, "csrf_token": csrf_token})
    response.set_cookie("csrf_token", csrf_token, httponly=True, samesite="strict")
    return response


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    cookie_csrf = request.cookies.get("csrf_token", "")
    if not validate_csrf_token(csrf_token) or csrf_token != cookie_csrf:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF inválido")

    stmt = select(User).where(User.email == email.lower().strip())
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.hashed_password):
        csrf = generate_csrf_token()
        resp = templates.TemplateResponse(
            "login.html",
            {"request": request, "csrf_token": csrf, "error": "Credenciales incorrectas"},
            status_code=401,
        )
        resp.set_cookie("csrf_token", csrf, httponly=True, samesite="strict")
        return resp

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario desactivado")

    if needs_rehash(user.hashed_password):
        user.hashed_password = hash_password(password)

    user.last_login = datetime.now(timezone.utc)
    await db.commit()

    token = create_access_token({
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "company_id": user.company_id,
        "branch_id": user.branch_id,
    })

    redirect = RedirectResponse(url="/dashboard", status_code=303)
    redirect.set_cookie(
        "access_token",
        token,
        httponly=True,
        samesite="strict",
        secure=False,
        max_age=60 * 480,
    )
    return redirect


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("access_token")
    return response
