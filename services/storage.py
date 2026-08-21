from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status
from db import models
from core.config import STORAGE_LIMIT_GB

def format_size(size_in_bytes: int) -> str:
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    elif size_in_bytes < 1024 * 1024:
        return f"{size_in_bytes / 1024:.1f} KB"
    elif size_in_bytes < 1024 * 1024 * 1024:
        return f"{size_in_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_in_bytes / (1024 * 1024 * 1024):.1f} GB"

def check_storage_quota(db: Session, incoming_bytes: int):
    total_limit_bytes = STORAGE_LIMIT_GB * 1024 * 1024 * 1024
    used_bytes = db.query(func.sum(models.Item.size_bytes)).filter(models.Item.is_folder == False).scalar() or 0
    
    if (used_bytes + incoming_bytes) > total_limit_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Upload ditolak: Kapasitas penyimpanan penuh. Batas kuota adalah {STORAGE_LIMIT_GB} GB."
        )