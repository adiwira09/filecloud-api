import os
from sqlalchemy.orm import Session, aliased
from db import models

def get_file_type(filename: str) -> str:
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext in ["pdf"]:
        return "pdf"
    elif ext in ["doc", "docx"]:
        return "doc"
    elif ext in ["txt"]:
        return "text"
    elif ext in ["jpg", "jpeg", "png", "gif", "webp"]:
        return "image"
    elif ext in ["ppt", "pptx"]:
        return "ppt"
    elif ext in ["mp4", "webm", "mkv", "avi"]:
        return "video"
    elif ext in ["mp3", "wav", "ogg", "flac"]:
        return "audio"
    return "other"

def remove_physical_files(file_paths: list[str]):
    for path in file_paths:
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

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
        db.query(models.Item.file_path)
        .filter(models.Item.id.in_(all_ids), models.Item.is_folder == False)
        .all()
    )
    file_paths = [file_row.file_path for file_row in files if file_row.file_path]

    deleted_count = db.query(models.Item).filter(models.Item.id.in_(all_ids)).delete(synchronize_session=False)
    db.commit()

    return deleted_count, file_paths