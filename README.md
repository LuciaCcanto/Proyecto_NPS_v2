# 360° NPS Platform

Plataforma SaaS monolítica de medición de satisfacción del cliente en tiempo real, inspirada en queop.com.

## Stack

- **Backend**: Python 3.13 · FastAPI · SQLAlchemy 2.0 (async) · Alembic
- **Frontend**: HTML5 · Pure CSS3 (Grid + Flexbox) · Vanilla JS
- **DB**: SQLite (dev) / PostgreSQL (prod) via `DATABASE_URL`
- **IA**: OpenAI API (análisis de sentimiento + drivers)
- **Seguridad**: Argon2id · JWT HttpOnly cookies · CSRF tokens · Parameterized ORM queries

## Estructura

```
Proyecto_NPS/
├── main.py               # Entry point FastAPI + lifespan + seed
├── requirements.txt
├── .env.example
├── app/
│   ├── core/
│   │   ├── config.py     # Pydantic Settings
│   │   ├── database.py   # Async SQLAlchemy engine
│   │   └── security.py   # Argon2id, JWT, CSRF
│   ├── models/           # SQLAlchemy ORM models
│   │   ├── user.py       # RBAC: SuperAdmin/CompanyAdmin/BranchOperator
│   │   ├── company.py    # Company + Branch + AIConfig
│   │   ├── survey.py     # Survey + Question + QuestionOption
│   │   ├── response.py   # Response + ResponseAnswer (NPS/CSAT/CES)
│   │   ├── ticket.py     # Ticket + AuditLog
│   │   └── checklist.py  # Checklist + LibroReclamos
│   ├── routers/          # FastAPI route handlers
│   │   ├── auth.py       # Login/Logout con CSRF
│   │   ├── dashboard.py  # Analytics view
│   │   ├── ingestion.py  # Multi-channel feedback + webhook
│   │   ├── tickets.py    # Incident management
│   │   ├── libro_reclamos.py
│   │   ├── checklist.py
│   │   └── notifications.py  # SSE endpoint
│   └── services/
│       ├── analytics_service.py  # NPS/CSAT/CES math engine
│       ├── openai_service.py     # AI sentiment analysis
│       ├── workflow_engine.py    # Rules engine + ticket auto-creation
│       ├── sse_manager.py        # Server-Sent Events broadcast
│       └── qr_service.py        # QR code generator
├── templates/            # Jinja2 HTML templates
└── static/
    ├── css/styles.css    # Corporate design system
    └── js/app.js         # Vanilla JS
```

## Inicio rápido

```bash
# 1. Crea entorno virtual
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # Linux/Mac

# 2. Instala dependencias
pip install -r requirements.txt

# 3. Configura variables de entorno
copy .env.example .env
# Edita .env con tu OPENAI_API_KEY

# 4. Ejecuta
python main.py
# o: uvicorn main:app --reload --port 8000
```

Visita: http://localhost:8000
Login demo: **admin@demo.com** / **Admin123!**

## Flujos clave

| URL | Descripción |
|-----|-------------|
| `/login` | Autenticación con CSRF |
| `/dashboard` | Panel analítico con NPS/CSAT/CES + Charts |
| `/survey/{slug}` | Encuesta pública (QR / Web / Tablet) |
| `/tickets` | Gestión de incidentes |
| `/reclamos` | Libro de Reclamos digital |
| `/checklist` | Auditoría operativa |
| `/api/events` | Server-Sent Events (SSE) |

## Seguridad (OWASP Top 10)

- **A01 Broken Access Control**: JWT + RBAC en cada ruta
- **A02 Cryptographic Failures**: Argon2id para passwords, HTTPS en prod
- **A03 Injection**: SQLAlchemy ORM (queries parametrizados, sin raw SQL)
- **A05 Security Misconfiguration**: Settings via pydantic-settings + .env
- **A07 Auth Failures**: Brute-force resistente (Argon2id), tokens HttpOnly
- **A10 SSRF**: Sin HTTP saliente arbitrario; solo OpenAI API controlado
