from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from auth.auth import get_current_user
from auth.models import User

def get_current_active_user(current_user: User = Depends(get_current_user)):
    return current_user

def get_admin_user(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


