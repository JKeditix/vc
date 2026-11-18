import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.config import FRONTEND_DIR, STORAGE_DIR, ensure_storage_dirs, settings
from backend.database import init_db
from backend.routers import clips, projects, settings as settings_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_storage_dirs()
    init_db()
    # Recover any projects left mid-processing if the server previously restarted
    from backend.database import SessionLocal
    from backend.models import Project

    db = SessionLocal()
    try:
        stale = db.query(Project).filter(Project.status.in_(["pending", "processing"])).all()
        for proj in stale:
            proj.status = "failed"
            proj.status_message = "Interrupted by server restart. Click Resume / Retry to continue."
        if stale:
            db.commit()
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount generated media (rendered clips & thumbnails) and frontend static assets
ensure_storage_dirs()
app.mount("/media", StaticFiles(directory=STORAGE_DIR), name="media")

static_dir = os.path.join(FRONTEND_DIR, "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Register modular API routers
app.include_router(projects.router)
app.include_router(clips.router)
app.include_router(settings_router.router)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": settings.PROJECT_NAME, "version": settings.VERSION}


@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    return HTMLResponse("<h1>VIRALCUT AI</h1><p>Frontend assets not found.</p>", status_code=404)
