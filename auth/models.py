from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from auth.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="user")

    # Relationship to permissions
    permissions = relationship("UserPermission", back_populates="user")


class UserPermission(Base):
    __tablename__ = "user_permission"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    api_name = Column(String)
    call_limit = Column(Integer, default=10)
    call_count = Column(Integer, default=0)
    last_reset = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="permissions")


