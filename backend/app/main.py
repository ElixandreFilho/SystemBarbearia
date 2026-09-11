from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import get_settings
from app.api.auth import router as auth_router
from app.api.services import router as services_router
from app.api.schedule import router as schedule_router
from app.api.availability import router as availability_router
from app.api.appointments import admin_router as admin_appointments_router
from app.api.appointments import router as appointments_router
from app.api.customers import router as customers_router
from app.dependencies import DbSession

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="API inicial do sistema de agendamento da barbearia.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(services_router)
app.include_router(schedule_router)
app.include_router(availability_router)
app.include_router(appointments_router)
app.include_router(admin_appointments_router)
app.include_router(customers_router)


@app.get("/health", tags=["system"])
async def health(db: DbSession) -> dict[str, str]:
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="banco indisponível") from exc
    return {"status": "ok", "environment": settings.environment, "database": "ok"}
