# from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Body, Form, Query
# from fastapi.responses import JSONResponse
# from auth.models import User
# from auth.auth import get_db, pwd_context, create_access_token
# from sqlalchemy.orm.attributes import flag_modified
# from sqlalchemy.orm import Session
# from utils import verify_jwt_token, check_api_limit
# from jose import JWTError, jwt



# router = APIRouter()

# @router.post("/profile/edit_new_password")
# def edit_new_password(
#     db: Session = Depends(get_db),
#     new_password: str = Body(...),
#     old_password: str = Body(...),
#     user_id: str = Depends(verify_jwt_token)
# ):
#     user_id = user_id[1]
#     user = db.query(User).filter(User.id == user_id).first()
    
#     if not user:
#         return JSONResponse(status_code=404, content={"message": "User not found"})

#     # Check the old password using the hash
#     if not pwd_context.verify(old_password, user.hashed_password):
#         return JSONResponse(status_code=400, content={"message": "password is incorrect"})

#     # Hash the new password and store it
#     user.hashed_password = pwd_context.hash(new_password)
#     db.commit()
#     flag_modified(user, "hashed_password") 
#     db.refresh(user)  

#     try:
#         token = create_access_token({"email": user.email, "sub": user.username, "id": user.id})

#     except JWTError:
#         raise JSONResponse(
#             status_code=500,
#             content={"detail": "Internal Server Error. Failed to generate access token."}
#         )
#     return JSONResponse(status_code=200, content={"message": "Password updated successfully",
#                                                    "access_token": token,
#                                                      "token_type": "bearer", 
#                                                      "user": {"username": user.username, "id": user.id, "email": user.email}})