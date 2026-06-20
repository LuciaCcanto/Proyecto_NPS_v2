from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    get_current_user_from_cookie,
    generate_csrf_token,
    validate_csrf_token,
    hash_password,
)
from app.models.company import Branch
from app.models.user import User, UserRole

router = APIRouter(prefix="/usuarios", tags=["usuarios"])
templates = Jinja2Templates(directory="templates")

_MASTER_ROLES = {UserRole.MASTER.value, UserRole.SUPERADMIN.value}
_ASSIGNABLE_ROLES = {UserRole.MASTER.value, UserRole.COMPANY_ADMIN.value, UserRole.BRANCH_OPERATOR.value}


def _require_master(request: Request) -> dict:
    try:
        user = get_current_user_from_cookie(request)
    except Exception:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    if user.get("role") not in _MASTER_ROLES:
        raise HTTPException(status_code=403, detail="Acceso restringido a roles master o superadmin")
    return user


async def _get_branches(db: AsyncSession, company_id: int) -> list:
    result = await db.execute(select(Branch).where(Branch.company_id == company_id))
    return result.scalars().all()


@router.get("", response_class=HTMLResponse)
async def list_users(request: Request, db: AsyncSession = Depends(get_db)):
    current_user = _require_master(request)
    company_id = current_user.get("company_id")
    current_id = int(current_user["sub"])

    stmt = select(User).where(User.id != current_id)
    if current_user.get("role") != UserRole.SUPERADMIN.value:
        stmt = stmt.where(User.company_id == company_id)
    stmt = stmt.order_by(User.created_at.desc())
    users = (await db.execute(stmt)).scalars().all()

    return templates.TemplateResponse("users.html", {
        "request": request,
        "user": current_user,
        "users": users,
        "mode": "list",
        "UserRole": UserRole,
    })


@router.get("/nuevo", response_class=HTMLResponse)
async def create_user_form(request: Request, db: AsyncSession = Depends(get_db)):
    current_user = _require_master(request)
    company_id = current_user.get("company_id")
    csrf_token = generate_csrf_token()
    branches = await _get_branches(db, company_id)

    resp = templates.TemplateResponse("users.html", {
        "request": request,
        "user": current_user,
        "mode": "create",
        "branches": branches,
        "csrf_token": csrf_token,
        "UserRole": UserRole,
    })
    resp.set_cookie("csrf_users", csrf_token, httponly=True, samesite="strict")
    return resp


@router.post("/nuevo")
async def create_user(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    branch_id: Optional[str] = Form(None),
    csrf_token: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    current_user = _require_master(request)
    company_id = current_user.get("company_id")

    cookie_csrf = request.cookies.get("csrf_users", "")
    if not validate_csrf_token(csrf_token) or csrf_token != cookie_csrf:
        raise HTTPException(status_code=403, detail="Token CSRF inválido")

    if role not in _ASSIGNABLE_ROLES:
        raise HTTPException(status_code=400, detail="Rol no permitido")

    existing = (await db.execute(select(User).where(User.email == email.strip().lower()))).scalar_one_or_none()
    if existing:
        branches = await _get_branches(db, company_id)
        new_csrf = generate_csrf_token()
        resp = templates.TemplateResponse("users.html", {
            "request": request,
            "user": current_user,
            "mode": "create",
            "branches": branches,
            "csrf_token": new_csrf,
            "UserRole": UserRole,
            "error": "Ya existe un usuario con ese correo electrónico.",
            "form_data": {"full_name": full_name, "email": email, "role": role},
        })
        resp.set_cookie("csrf_users", new_csrf, httponly=True, samesite="strict")
        return resp

    branch_id_int = int(branch_id) if branch_id and branch_id.strip() else None
    new_user = User(
        email=email.strip().lower(),
        hashed_password=hash_password(password),
        full_name=full_name.strip(),
        role=role,
        company_id=company_id,
        branch_id=branch_id_int,
        is_active=True,
    )
    db.add(new_user)
    await db.commit()
    return RedirectResponse(url="/usuarios", status_code=303)


@router.get("/{user_id}/editar", response_class=HTMLResponse)
async def edit_user_form(request: Request, user_id: int, db: AsyncSession = Depends(get_db)):
    current_user = _require_master(request)
    company_id = current_user.get("company_id")

    stmt = select(User).where(User.id == user_id)
    if current_user.get("role") != UserRole.SUPERADMIN.value:
        stmt = stmt.where(User.company_id == company_id)
    target = (await db.execute(stmt)).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    csrf_token = generate_csrf_token()
    branches = await _get_branches(db, company_id)

    resp = templates.TemplateResponse("users.html", {
        "request": request,
        "user": current_user,
        "mode": "edit",
        "target_user": target,
        "branches": branches,
        "csrf_token": csrf_token,
        "UserRole": UserRole,
    })
    resp.set_cookie("csrf_users", csrf_token, httponly=True, samesite="strict")
    return resp


@router.post("/{user_id}/editar")
async def edit_user(
    request: Request,
    user_id: int,
    full_name: str = Form(...),
    email: str = Form(...),
    password: Optional[str] = Form(None),
    role: str = Form(...),
    branch_id: Optional[str] = Form(None),
    is_active: Optional[str] = Form(None),
    csrf_token: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    current_user = _require_master(request)
    company_id = current_user.get("company_id")

    cookie_csrf = request.cookies.get("csrf_users", "")
    if not validate_csrf_token(csrf_token) or csrf_token != cookie_csrf:
        raise HTTPException(status_code=403, detail="Token CSRF inválido")

    stmt = select(User).where(User.id == user_id)
    if current_user.get("role") != UserRole.SUPERADMIN.value:
        stmt = stmt.where(User.company_id == company_id)
    target = (await db.execute(stmt)).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if role not in _ASSIGNABLE_ROLES:
        raise HTTPException(status_code=400, detail="Rol no permitido")

    target.full_name = full_name.strip()
    target.email = email.strip().lower()
    target.role = role
    target.branch_id = int(branch_id) if branch_id and branch_id.strip() else None
    target.is_active = (is_active == "on")
    if password and password.strip():
        target.hashed_password = hash_password(password)

    await db.commit()
    return RedirectResponse(url="/usuarios", status_code=303)
