import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime
from db.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)

class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("items.id"), nullable=True)
    name = Column(String, index=True)
    is_folder = Column(Boolean, default=False)
    file_type = Column(String)
    size_bytes = Column(Integer, default=0)
    file_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)