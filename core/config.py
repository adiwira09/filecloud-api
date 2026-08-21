import os
from dotenv import load_dotenv

load_dotenv()

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
CHUNK_DIR = os.getenv("CHUNK_DIR", "./temp_chunks")
STORAGE_LIMIT_GB = float(os.getenv("STORAGE_LIMIT_GB", "10"))
CORS_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")]
FRONTEND_DIST_DIR = os.getenv("FRONTEND_DIST_DIR", "../frontend/dist")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./filecloud.db")

DISALLOWED_EXTENSIONS = {
    "html", "htm", "xhtml", "svg", "js", "jsx", "ts", "tsx", 
    "php", "phtml", "py", "sh", "bat", "cmd", "exe", "cgi"
}
ALLOWED_INLINE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp", "pdf", "mp4", "mp3", "wav", "txt"}