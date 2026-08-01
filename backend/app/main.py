from fastapi import FastAPI
from backend.app.core.config import settings
from backend.app.api.auth import router as auth_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Enterprise Multi-Agent Finance Platform",
)

app.include_router(
    auth_router,
    prefix=settings.API_V1_STR
)

@app.get("/")
def home():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}"
    }


@app.get("/health")
def health():
    return {
        "status": "Healthy"
    }


