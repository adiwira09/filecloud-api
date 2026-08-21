from typing import Optional

from fastapi import APIRouter, Depends, Form
from sqlalchemy.orm import Session

from db.database import get_db
from db import models
from schemas.file import ItemActionResponse
from core.security import verify_access

router = APIRouter(dependencies=[Depends(verify_access)])

@router.post("/folders", response_model=ItemActionResponse)
def create_folder(
    folder_name: str = Form(...), 
    parent_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    new_folder = models.Item(
        name=folder_name,
        is_folder=True,
        file_type="folder",
        size_bytes=0,
        file_path=None,
        parent_id=parent_id
    )
    db.add(new_folder)
    db.commit()
    db.refresh(new_folder)

    return ItemActionResponse(message="Folder berhasil dibuat", item_id=new_folder.id)