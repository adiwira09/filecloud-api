import os
import uuid
import datetime
import mimetypes
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy.orm import Session

import utils

from db.database import get_db
from db import models

from schemas.file import ItemActionResponse

from core.security import verify_access
from core.config import DISALLOWED_EXTENSIONS

from services.file_service import check_storage_quota
from services.storage.base import StorageService
from services.storage.local import LocalStorage
from services.storage.factory import get_storage_service

router = APIRouter(dependencies=[Depends(verify_access)])

@router.post("/upload/request-url")
def request_upload_url(
    filename: str = Form(...),
    file_size: int = Form(...),
    content_type: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage_service)
):
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext in DISALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Upload ditolak: File dengan ekstensi '.{ext}' tidak diperbolehkan"
        )

    check_storage_quota(db, file_size)

    object_key = f"{uuid.uuid4().hex}"
    
    if not content_type:
        content_type, _ = mimetypes.guess_type(filename)

    try:
        upload_url = storage.get_upload_url(object_key, content_type=content_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal memproses URL upload: {str(e)}")

    return {
        "upload_url": upload_url,
        "object_key": object_key
    }

@router.put("/upload/local-direct")
async def local_upload_direct(
    object_key: str,
    request: Request,
    storage: StorageService = Depends(get_storage_service)
):
    if not isinstance(storage, LocalStorage):
        raise HTTPException(status_code=400, detail="Endpoint ini hanya khusus untuk Local Storage")

    file_path = storage._get_path(object_key)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(file_path, "wb") as buffer:
            async for chunk in request.stream():
                buffer.write(chunk)
    except Exception as e:
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"Gagal menulis file lokal: {str(e)}")

    return {"message": "Upload lokal berhasil"}

@router.post("/upload/complete", response_model=ItemActionResponse)
def complete_upload(
    object_key: str = Form(...),
    filename: str = Form(...),
    file_size: int = Form(...),
    parent_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage_service)
):
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext in DISALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Ekstensi file tidak diperbolehkan")

    if not storage.exists(object_key):
        raise HTTPException(status_code=400, detail="File belum berhasil terunggah ke storage")

    safe_name = os.path.basename(filename)
    file_type = utils.get_file_type(filename)

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
        raise HTTPException(status_code=500, detail=f"Gagal menyimpan metadata file: {str(e)}")

    return ItemActionResponse(message="File berhasil diunggah penuh", item_id=new_item.id)
