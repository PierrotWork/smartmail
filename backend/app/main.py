"""Точка входа FastAPI-приложения."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import settings
from app.modules.auth.router import router as auth_router
from app.modules.campaigns.router import router as campaigns_router
from app.modules.clients.router import router as clients_router
from app.modules.settings.router import router as settings_router
from app.modules.templates.router import router as templates_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: сюда позже добавим прогрев кэша, healthcheck внешних сервисов и т.п.
    yield
    # shutdown


app = FastAPI(
    title="SmartMail Campaigns API",
    version=__version__,
    description="API для управления email-рассылками и клиентской базой.",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok", "version": __version__, "env": settings.app_env}


# Роутеры модулей
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(clients_router, prefix="/api/v1/clients", tags=["clients"])
app.include_router(templates_router, prefix="/api/v1/templates", tags=["templates"])
app.include_router(campaigns_router, prefix="/api/v1/campaigns", tags=["campaigns"])
app.include_router(settings_router, prefix="/api/v1/settings", tags=["settings"])
