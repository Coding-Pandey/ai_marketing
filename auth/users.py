from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from auth.schemas import UserCreate, UserOut, Token
from auth.models import User
from auth.auth import get_db, get_password_hash, authenticate_user, create_access_token
from auth.deps import get_current_active_user, get_admin_user
from auth.auth import oauth2_scheme
from fastapi.responses import JSONResponse
from auth.database import Base, engine
from pydantic import BaseModel, EmailStr
from jose import JWTError, jwt

class APIException(HTTPException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)

class EmailPasswordLogin(BaseModel):
    email: EmailStr
    password: str

router = APIRouter()

Base.metadata.create_all(bind=engine)

@router.post("/register", response_model=UserOut)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()

    db_user_email = db.query(User).filter(User.email == user.email).first()

    if db_user_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_pw = get_password_hash(user.password)

    new_user = User(username=user.username, email=user.email, hashed_password=hashed_pw)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.post("/login", response_model=Token)
async def login_for_access_token(login_data: EmailPasswordLogin, db=Depends(get_db)):
    try:
      
        if not login_data.email or not login_data.password:
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bad Request. Email and password are required."
            )

        user = authenticate_user(db, email=login_data.email, password=login_data.password)
        
        if not user:
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Incorrect email or password"
            )

        if hasattr(user, 'is_active') and not user.is_active:
            raise APIException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden. User account is not active."
            )

        try:
            token = create_access_token({"sub": user.email})
        except JWTError:
            raise APIException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal Server Error. Failed to generate access token."
            )

        return {"access_token": token, "token_type": "bearer", "user": user.username}

    except APIException as e:
        raise e
    except Exception as e:
        raise APIException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error. An unexpected error occurred."
        )


@router.get("/me", response_model=UserOut)
def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user


@router.get("/admin/users", response_model=list[UserOut])
def list_all_users(db: Session = Depends(get_db), _: User = Depends(get_admin_user)):
    return db.query(User).all()


@router.post("/logout")
def logout(token: str = Depends(oauth2_scheme)):
    # No server-side action for stateless JWT
    return JSONResponse(content={"message": "Successfully logged out. Please delete token on client."})
