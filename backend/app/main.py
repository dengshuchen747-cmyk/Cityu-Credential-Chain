from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import admin, auth, campaigns, claims, credentials


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Synchronous FastAPI gateway for CityU academic credentials.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.app_env}


app.include_router(auth.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(campaigns.router, prefix="/api/v1")
app.include_router(claims.router, prefix="/api/v1")
app.include_router(credentials.router, prefix="/api/v1")
