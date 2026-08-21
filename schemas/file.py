from pydantic import BaseModel
from typing import List, Optional

class BulkDeleteRequest(BaseModel):
    item_ids: List[int]

class ItemResponse(BaseModel):
    id: int
    parent_id: Optional[int] = None
    name: str
    type: str
    modified: str
    size: str
    size_bytes: int
    is_folder: bool

    class Config:
        from_attributes = True

class ItemActionResponse(BaseModel):
    message: str
    item_id: int