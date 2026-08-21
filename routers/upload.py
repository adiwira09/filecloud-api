import os
import uuid
import shutil
import datetime
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session

from db.database import get_db
from db import models
from schemas.file import ItemActionResponse
from schemas.common import MessageResponse
from core.security import verify_access
from core.config import UPLOAD_DIR, CHUNK_DIR, DISALLOWED_EXTENSIONS
from services.storage import check_storage_quota
from services.file_service import get_file_type

router = APIRouter(dependencies=[Depends(verify_access)])

@router.post("/upload", response_model=ItemActionResponse)
def upload_file(
    file: UploadFile = File(...), 
    parent_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
    if ext in DISALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Upload ditolak: File dengan ekstensi '.{ext}' tidak diperbolehkan di-izinkan"
        )

    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)
    
    check_storage_quota(db, file_size)

    safe_name = os.path.basename(file.filename)
    unique_filename = f"{uuid.uuid4().hex}_{safe_name}"
    file_location = os.path.join(UPLOAD_DIR, unique_filename)

    with open(file_location, "wb") as f:
        shutil.copyfileobj(file.file, f)

    size_bytes = os.path.getsize(file_location)
    file_type = get_file_type(file.filename)

    new_item = models.Item(
        name=safe_name,
        is_folder=False,
        file_type=file_type,
        size_bytes=size_bytes,
        file_path=file_location,
        created_at=datetime.datetime.now(datetime.timezone.utc),
        parent_id=parent_id
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)

    return ItemActionResponse(message="File uploaded successfully", item_id=new_item.id)

@router.post("/upload/chunk", response_model=MessageResponse)
def upload_file_chunk(
    upload_id: str = Form(...),
    chunk_index: int = Form(...),
    file: UploadFile = File(...)
):
    target_dir = os.path.join(CHUNK_DIR, upload_id)
    os.makedirs(target_dir, exist_ok=True)
    chunk_path = os.path.join(target_dir, f"chunk_{chunk_index}")

    with open(chunk_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    return MessageResponse(message=f"Chunk {chunk_index} uploaded successfully")

@router.post("/upload/complete", response_model=ItemActionResponse)
def complete_upload(
    upload_id: str = Form(...),
    filename: str = Form(...),
    total_chunks: int = Form(...),
    parent_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext in DISALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Ekstensi file tidak di-izinkan")

    chunk_dir = os.path.join(CHUNK_DIR, upload_id)

    total_incoming_bytes = 0
    for i in range(total_chunks):
        chunk_path = os.path.join(chunk_dir, f"chunk_{i}")
        if os.path.exists(chunk_path):
            total_incoming_bytes += os.path.getsize(chunk_path)

    check_storage_quota(db, incoming_bytes=total_incoming_bytes)

    safe_name = os.path.basename(filename)
    unique_filename = f"{uuid.uuid4().hex}_{safe_name}"
    final_file_path = os.path.join(UPLOAD_DIR, unique_filename)

    try:
        with open(final_file_path, "wb") as final_file:
            for i in range(total_chunks):
                chunk_path = os.path.join(chunk_dir, f"chunk_{i}")
                if not os.path.exists(chunk_path):
                    raise HTTPException(status_code=400, detail=f"Potongan file ke-{i} hilang")
                with open(chunk_path, "rb") as chunk_file:
                    shutil.copyfileobj(chunk_file, final_file)
        
        shutil.rmtree(chunk_dir, ignore_errors=True)
    except Exception as e:
        if os.path.exists(final_file_path):
            os.remove(final_file_path)
        raise HTTPException(status_code=500, detail=f"Gagal menggabungkan file: {str(e)}")

    size_bytes = os.path.getsize(final_file_path)
    file_type = get_file_type(filename)

    new_item = models.Item(
        name=safe_name,
        is_folder=False,
        file_type=file_type,
        size_bytes=size_bytes,
        file_path=final_file_path,
        created_at=datetime.datetime.now(datetime.timezone.utc),
        parent_id=parent_id
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)

    return ItemActionResponse(message="File berhasil diunggah penuh", item_id=new_item.id)