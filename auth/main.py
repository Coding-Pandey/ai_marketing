# from fastapi import FastAPI, Depends, HTTPException
# from fastapi.security import OAuth2PasswordRequestForm
# from auth import authenticate_user, create_access_token, get_db
# from database import Base, engine
# from users import router as users_router
# from schemas import Token
# from pydantic import BaseModel, EmailStr

# class EmailPasswordLogin(BaseModel):
#     email: EmailStr
#     password: str


# app = FastAPI()

# Base.metadata.create_all(bind=engine)

# app.include_router(users_router)

# @app.post("/login", response_model=Token)
# def login_for_access_token(login_data: EmailPasswordLogin, db=Depends(get_db)):

#     user = authenticate_user(db, email=login_data.email, password=login_data.password)

#     if not user: 
#         raise HTTPException(status_code=401, detail="Incorrect email or password")
    
#     token = create_access_token({"sub": user.email})

#     return {"access_token": token, "token_type": "bearer"}



