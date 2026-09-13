from sqlalchemy.orm import Session, aliased
from sqlalchemy import func

from fastapi import HTTPException, status

from db import models
from core.config import STORAGE_LIMIT_GB

from services.storage.base import StorageService

def check_storage_quota(db: Session, incoming_bytes: int):
    total_limit_bytes = STORAGE_LIMIT_GB * 1024 * 1024 * 1024
    used_bytes = db.query(func.sum(models.Item.size_bytes)).filter(models.Item.is_folder == False).scalar() or 0
    
    if (used_bytes + incoming_bytes) > total_limit_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Upload ditolak: Kapasitas penyimpanan penuh. Batas kuota adalah {STORAGE_LIMIT_GB} GB."
        )
    
def delete_item(item_ids: list[int], db: Session) -> tuple[int, list[str]]:
    if not item_ids:
        return 0, []

    item_alias = aliased(models.Item)
    item_hierarchy = (
        db.query(models.Item.id)
        .filter(models.Item.id.in_(item_ids))
        .cte(name="item_hierarchy", recursive=True)
    )
    item_hierarchy = item_hierarchy.union_all(
        db.query(item_alias.id)
        .filter(item_alias.parent_id == item_hierarchy.c.id)
    )
    
    all_ids = [row[0] for row in db.query(item_hierarchy.c.id).all()]
    if not all_ids:
        return 0, []

    files = (
        db.query(models.Item)
        .filter(models.Item.id.in_(all_ids), models.Item.is_folder == False)
        .all()
    )

    object_keys = [item.object_key for item in files if item.object_key]

    # hapus metadata database
    deleted_count = (
        db.query(models.Item)
        .filter(models.Item.id.in_(all_ids))
        .delete(synchronize_session=False)
    )
    db.commit()

    return deleted_count, object_keys

def delete_storage_objects(
    storage: StorageService,
    object_keys: list[str]
):
    for object_key in object_keys:
        try:
            storage.delete(object_key)
            print(f"Berhasil menghapus file di storage: {object_key}")
        except Exception as e:
            print(f"Gagal menghapus file di storage: {object_key} | {type(e).__name__}: {e}")