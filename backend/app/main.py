from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import dashboard, judgments
from app.core.config import get_settings
from app.core.database import init_db

settings = get_settings()

app = FastAPI(title="CCMS-Sahayak", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    settings.pdf_storage_dir.mkdir(parents=True, exist_ok=True)
    init_db()


app.mount("/storage/pdfs", StaticFiles(directory=settings.pdf_storage_dir), name="pdfs")
app.include_router(judgments.router, prefix="/api/v1/judgments", tags=["judgments"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
