import mimetypes
import os
import uuid
import shutil
import datetime
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session

import utils

from db.database import get_db
from db import models

from schemas.file import ItemActionResponse
from schemas.common import MessageResponse

from core.security import verify_access
from core.config import CHUNK_DIR, DISALLOWED_EXTENSIONS

from services.file_service import check_storage_quota
from services.storage.base import StorageService
from services.storage.factory import get_storage_service

router = APIRouter(dependencies=[Depends(verify_access)])

@router.post("/upload", response_model=ItemActionResponse)
def upload_file(
    file: UploadFile = File(...), 
    parent_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage_service)
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
    object_key = f"files/{uuid.uuid4().hex}"

    try:
        storage.upload(file.file, object_key, content_type=file.content_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal mengunggah file ke storage: {str(e)}")

    file_type = utils.get_file_type(file.filename)

    new_item = models.Item(
        name=safe_name,
        is_folder=False,
        file_type=file_type,
        size_bytes=file_size,
        object_key=object_key,
        created_at=datetime.datetime.now(datetime.timezone.utc),
        parent_id=parent_id
    )
    try:
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
    except Exception as e:
        db.rollback()
        try:
            storage.delete(object_key)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Gagal menyimpan metadata file ke database: {str(e)}")
    
    return ItemActionResponse(message="File uploaded successfully", item_id=new_item.id)

@router.post("/upload/chunk", response_model=MessageResponse)
def upload_file_chunk(
    upload_id: str = Form(...),
    chunk_index: int = Form(...),
    file: UploadFile = File(...)
):
    try:
        uuid.UUID(upload_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="upload_id tidak valid")

    if chunk_index < 0:
        raise HTTPException(status_code=400, detail="chunk_index tidak valid")
    
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
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage_service)
):
    try:
        uuid.UUID(upload_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="upload_id tidak valid")
    
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext in DISALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Ekstensi file tidak di-izinkan")

    if total_chunks <= 0:
        raise HTTPException(status_code=400, detail="Total chunks tidak valid")

    chunk_dir = os.path.join(CHUNK_DIR, upload_id)
    if not os.path.isdir(chunk_dir):
        raise HTTPException(status_code=404, detail="Data upload tidak ditemukan")

    chunk_paths = []
    for i in range(total_chunks):
        chunk_path = os.path.join(chunk_dir, f"chunk_{i}")
        if not os.path.isfile(chunk_path):
            raise HTTPException(
                status_code=400,
                detail=f"Potongan file ke-{i} hilang"
            )

        chunk_paths.append(chunk_path)

    total_incoming_bytes = sum(os.path.getsize(p) for p in chunk_paths)
    if total_incoming_bytes <= 0:
        raise HTTPException(status_code=400, detail="File kosong atau tidak valid")
    
    check_storage_quota(db, incoming_bytes=total_incoming_bytes)

    safe_name = os.path.basename(filename)
    merged_filename = f".merged_{uuid.uuid4().hex}"
    merged_file_path = os.path.join(chunk_dir, merged_filename)
    object_key = f"files/{uuid.uuid4().hex}"
    
    try:
        with open(merged_file_path, "wb") as merged_file:
            for chunk_path in chunk_paths:
                with open(chunk_path, "rb") as chunk_file:
                    shutil.copyfileobj(chunk_file, merged_file, length=1024*1024)

        content_type, _ = mimetypes.guess_type(filename)
        with open(merged_file_path, "rb") as merged_file:
            storage.upload(merged_file, object_key, content_type=content_type)

        file_type = utils.get_file_type(filename)

        new_item = models.Item(
            name=safe_name,
            is_folder=False,
            file_type=file_type,
            size_bytes=total_incoming_bytes,
            object_key=object_key,
            created_at=datetime.datetime.now(datetime.timezone.utc),
            parent_id=parent_id
        )
        db.add(new_item)
        db.commit()
        db.refresh(new_item)

    except Exception as e:
        db.rollback()
        try:
            storage.delete(object_key)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Gagal menyelesaikan upload: {str(e)}")
    
    finally:
        shutil.rmtree(chunk_dir, ignore_errors=True)

    return ItemActionResponse(message="File berhasil diunggah penuh", item_id=new_item.id)