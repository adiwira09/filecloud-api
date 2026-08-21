from pydantic import BaseModel

class MessageResponse(BaseModel):
    message: str

class StorageStatusResponse(BaseModel):
    used_bytes: int
    used_formatted: str
    total_formatted: str
    percentage: float