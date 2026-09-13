import os
from dotenv import load_dotenv

load_dotenv()

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

# object storage provider: "local", "s3", or "gcs"
STORAGE_PROVIDER = os.getenv("STORAGE_PROVIDER", "local")

## local storage configuration
LOCAL_STORAGE_PATH = os.getenv("LOCAL_STORAGE_PATH", "./uploads")

## S3 configuration
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", "")
S3_REGION_NAME = os.getenv("S3_REGION_NAME", "")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "")

## GCS configuration
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "")