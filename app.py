import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core.config import CORS_ORIGINS, FRONTEND_DIST_DIR, UPLOAD_DIR, CHUNK_DIR
from core.security import rate_limit_auth_middleware
from db.database import engine, Base
from routers import files, upload, folders
from schemas.common import MessageResponse

Base.metadata.create_all(bind=engine)
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CHUNK_DIR, exist_ok=True)

app = FastAPI(title="FileCloud API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(rate_limit_auth_middleware)

app.include_router(files.router, prefix="/api", tags=["Files"])
app.include_router(upload.router, prefix="/api", tags=["Upload"])
app.include_router(folders.router, prefix="/api", tags=["Folders"])

@app.get("/status-check", response_model=MessageResponse, tags=["Health"])
def root():
    return MessageResponse(message="API FileCloud is running")

if os.path.exists(FRONTEND_DIST_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST_DIR, html=True), name="static")
elif os.path.exists("./dist"):
    app.mount("/", StaticFiles(directory="./dist", html=True), name="static")