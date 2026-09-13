import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime
from db.database import Base

class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("items.id"), nullable=True)
    name = Column(String, index=True)
    is_folder = Column(Boolean, default=False)
    file_type = Column(String)
    size_bytes = Column(Integer, default=0)
    object_key = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)