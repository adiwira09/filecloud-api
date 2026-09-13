import io
import os
import secrets
import time
import mimetypes
from typing import List, Optional
from PIL import Image, ImageOps

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Response, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

import utils

from db.database import get_db
from db import models

from schemas.file import ItemResponse, BulkDeleteRequest
from schemas.common import MessageResponse, StorageStatusResponse

from core.security import verify_access
from core.config import ALLOWED_INLINE_EXTENSIONS, STORAGE_LIMIT_GB

from services.file_service import delete_item, delete_storage_objects
from services.storage.base import StorageService
from services.storage.factory import get_storage_service
from services.storage.local import LocalStorage

router = APIRouter(dependencies=[Depends(verify_access)])
public_router = APIRouter()

_download_tokens: dict = {}
_TOKEN_TTL = 30 # 30 detik

def _purge_expired_tokens():
    now = time.time()
    expired = [k for k, v in _download_tokens.items() if v["expires_at"] < now]
    for k in expired:
        _download_tokens.pop(k, None)

@router.get("/files", response_model=List[ItemResponse])
def get_files(
    search: Optional[str] = None, 
    parent_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Item)
    if search:
        query = query.filter(models.Item.name.ilike(f"%{search}%"))
    else:
        query = query.filter(models.Item.parent_id == parent_id)
    
    items = query.order_by(models.Item.is_folder.desc(), models.Item.created_at.desc()).all()
    folder_ids = [item.id for item in items if item.is_folder]

    counts_dict = {}
    if folder_ids:
        counts = (
            db.query(models.Item.parent_id, func.count(models.Item.id))
            .filter(models.Item.parent_id.in_(folder_ids))
            .group_by(models.Item.parent_id)
            .all()
        )
        counts_dict = {pid: count for pid, count in counts}

    result = []
    for item in items:
        if item.is_folder:
            count = counts_dict.get(item.id, 0)
            size_str = f"{count} items"
        else:
            size_str = utils.format_size(item.size_bytes)
            
        result.append({
            "id": item.id,
            "parent_id": item.parent_id,
            "name": item.name,
            "type": "folder" if item.is_folder else item.file_type,
            "modified": item.created_at.strftime("%b %d, %Y"),
            "size": size_str,
            "size_bytes": item.size_bytes,
            "is_folder": item.is_folder
        })
    return result

@router.post("/download-token/{item_id}")
def create_download_token(
    item_id: int, 
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage_service)
):
    item = db.query(models.Item).filter(models.Item.id == item_id).first()

    if not item or item.is_folder:
        raise HTTPException(status_code=404, detail="File tidak ditemukan")

    if not item.object_key:
        raise HTTPException(status_code=404, detail="Object key file tidak ditemukan")

    # local storage
    if isinstance(storage, LocalStorage):
        try:
            file_path = storage.get_file_path(item.object_key)
        except ValueError:
            raise HTTPException(status_code=400, detail="Object key tidak valid")

        if not os.path.isfile(file_path):
            raise HTTPException(status_code=404, detail="File tidak ditemukan di storage")

        _purge_expired_tokens()
        token = secrets.token_urlsafe(32)
        _download_tokens[token] = {
            "item_id": item.id,
            "expires_at": time.time() + _TOKEN_TTL
        }

        return {
            "download_token": token,
        }

    # object storage
    try:
        if not storage.exists(item.object_key):
            raise HTTPException(status_code=404, detail="File tidak ditemukan di storage")

        download_url = storage.get_download_url(
            item.object_key, 
            expiration=_TOKEN_TTL,
            download=True,
            filename=item.name
        )

        return {
            "download_url": download_url
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error generating download URL: {str(e)}")

@public_router.get("/download/{download_token}")
def download_file(
    download_token: str, 
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage_service)
):
    _purge_expired_tokens()

    entry = _download_tokens.pop(download_token, None)
    if not entry or entry["expires_at"] < time.time():
        raise HTTPException(status_code=410, detail="Link download tidak valid atau sudah kadaluarsa")

    item = db.query(models.Item).filter(models.Item.id == entry["item_id"]).first()

    if not item or item.is_folder:
        raise HTTPException(status_code=404, detail="File tidak ditemukan")

    if not item.object_key:
        raise HTTPException(status_code=404, detail="Object key file tidak ditemukan")

    if not isinstance(storage, LocalStorage):
        raise HTTPException(status_code=400, detail="Endpoint ini hanya digunakan untuk local storage")

    try:
        file_path = storage.get_file_path(item.object_key)
    except ValueError:
        raise HTTPException(status_code=400, detail="Object key tidak valid")
        
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File fisik tidak ditemukan di server")

    mime_type, _ = mimetypes.guess_type(item.name)

    return FileResponse(
        path=file_path,
        filename=item.name,
        media_type=mime_type or "application/octet-stream"
    )

@router.delete("/files/{item_id}", response_model=MessageResponse)
def delete_file(
    item_id: int, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage_service)
):
    deleted_count, object_keys = delete_item([item_id], db)
    if deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item tidak ditemukan")

    if object_keys:
        background_tasks.add_task(delete_storage_objects, storage, object_keys)

    return MessageResponse(message=f"{deleted_count} item berhasil dihapus")

@router.post("/files/bulk-delete", response_model=MessageResponse)
def bulk_delete_files(
    payload: BulkDeleteRequest, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage_service)
):
    if not payload.item_ids:
        raise HTTPException(status_code=400, detail="Tidak ada item yang dipilih untuk dihapus")

    deleted_count, object_keys = delete_item(payload.item_ids, db)
    if object_keys:
        background_tasks.add_task(delete_storage_objects, storage, object_keys)
        
    return MessageResponse(message=f"{deleted_count} item berhasil dihapus")

@router.get("/preview/{item_id}")
def preview_file(
    item_id: int, 
    size: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage_service)
):
    item = db.query(models.Item).filter(models.Item.id == item_id).first()

    if not item or item.is_folder:
        raise HTTPException(status_code=404, detail="File tidak ditemukan")

    if not item.object_key:
        raise HTTPException(status_code=404, detail="Object key file tidak ditemukan")

    ext = item.name.split(".")[-1].lower() if "." in item.name else ""
    if size == "thumb" and ext in {"jpg", "jpeg", "png", "webp"}:
        try:
            if not storage.exists(item.object_key):
                raise HTTPException(status_code=404, detail="File tidak ditemukan di storage")

            with storage.download(item.object_key) as file_stream:
                with Image.open(file_stream) as img:
                    img = ImageOps.exif_transpose(img)
                    img.thumbnail((300, 300))
                    buffer = io.BytesIO()
                
                    fmt = "JPEG" if ext in ["jpg", "jpeg"] else ext.upper()
                    if fmt == "JPEG":
                        if img.mode in {"RGBA", "LA", "P"}:
                            img = img.convert("RGB")
                            
                    img.save(buffer, format=fmt, quality=75)
                    buffer.seek(0)
                
                    return Response(
                        content=buffer.getvalue(), 
                        media_type="image/jpeg" if fmt == "JPEG" else f"image/{ext}",
                        headers={"Cache-Control": "private, max-age=86400"}
                    )
        except HTTPException:
            raise

        except Exception:
            raise HTTPException(status_code=500, detail="Tidak dapat membuat preview untuk file ini")

    if not isinstance(storage, LocalStorage):
        try:
            if not storage.exists(item.object_key):
                raise HTTPException(status_code=404, detail="File tidak ditemukan di storage")

            preview_url = storage.get_download_url(item.object_key, expiration=_TOKEN_TTL)
            
            return {
                "preview_url": preview_url,
                "name": item.name,
                "file_type": item.file_type,
                "mime_type": mimetypes.guess_type(item.name)[0] or "application/octet-stream"
            }

        except HTTPException:
            raise

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Gagal membuat preview URL: {str(e)}")

    try:
        file_path = storage.get_file_path(item.object_key)
    except ValueError:
        raise HTTPException(status_code=400, detail="Object key tidak valid")

    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File fisik tidak ditemukan di server")

    disposition = "inline" if ext in ALLOWED_INLINE_EXTENSIONS else "attachment"
    mime_type, _ = mimetypes.guess_type(item.name)

    return FileResponse(
        path=file_path,
        media_type=mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'{disposition}; filename="{item.name}"',
            "Cache-Control": "private, max-age=86400"
        }
    )
        
@router.get("/storage", response_model=StorageStatusResponse)
def get_storage_status(db: Session = Depends(get_db)):
    total_limit_bytes = STORAGE_LIMIT_GB * 1024 * 1024 * 1024
    used_bytes = db.query(func.sum(models.Item.size_bytes)).filter(models.Item.is_folder == False).scalar() or 0
    percentage = round((used_bytes / total_limit_bytes) * 100, 1)

    return StorageStatusResponse(
        used_bytes=used_bytes,
        used_formatted=utils.format_size(used_bytes),
        total_formatted=f"{STORAGE_LIMIT_GB} GB",
        percentage=percentage
    )