from fastapi import APIRouter, Depends, HTTPException, status,  Request
from sqlalchemy.orm import Session
from auth.schemas import UserCreate, UserOut, Token, User, Usergoogle
from auth.models import User, UserPermission
from auth.auth import get_db, get_password_hash, authenticate_user, create_access_token
from auth.deps import get_current_active_user, get_admin_user
from auth.auth import oauth2_scheme
from fastapi.responses import JSONResponse
from auth.database import Base, engine
from pydantic import BaseModel, EmailStr
from starlette.middleware.sessions import SessionMiddleware
from jose import JWTError, jwt
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from datetime import datetime, timedelta
from auth.permission import get_default_permissions
from auth.utiles import create_permissions_for_user
import os

class APIException(HTTPException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)

class EmailPasswordLogin(BaseModel):
    email: EmailStr
    password: str

router = APIRouter()

Base.metadata.create_all(bind=engine)
# Add session middleware for OAuth
config = Config(".env")

oauth = OAuth(config)
oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)


@router.post("/register", response_model=UserOut)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()

    db_user_email = db.query(User).filter(User.email == user.email).first()


    if db_user_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_pw = get_password_hash(user.password)

    new_user = User(username=user.username, email=user.email, hashed_password=hashed_pw, role=user.role)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # default_permissions = get_default_permissions(role=new_user.role)
    dataa = create_permissions_for_user(new_user, db)
    # for api_name, call_limit in default_permissions.items():
    #     permission = UserPermission(
    #         user_id=new_user.id,
    #         api_name=api_name,
    #         call_limit=call_limit,
    #         call_count=0,
    #         last_reset=datetime.utcnow()
    #     )
    #     db.add(permission)

    # db.commit()
    print(dataa)

    return new_user


@router.post("/google_login")
async def google_login(user: Usergoogle, db: Session = Depends(get_db)):
    try:
        if not user.email or not user.username or not user.oAuthId:
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email, username, and oAuthId are required."
            )

        user_by_email = db.query(User).filter(User.email == user.email).first()
        user_by_oauth = db.query(User).filter(User.oAuthId == user.oAuthId).first()

        # Case 1: Email exists
        if user_by_email:
            # a. OAuth ID already assigned
            if user_by_oauth:
                if user_by_oauth.email != user.email:
                    raise APIException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="OAuth ID already used by another account."
                    )
                # OAuth ID belongs to this user → return token
                token = create_access_token({
                    "email": user_by_email.email,
                    "sub": user_by_email.username,
                    "id": user_by_email.id
                })
                return {
                    "access_token": token,
                    "token_type": "bearer",
                    "user": {
                        "username": user_by_email.username,
                        "id": user_by_email.id,
                        "email": user_by_email.email
                    }
                }
            else:
               
                user_by_email.oAuthId = user.oAuthId
                db.commit()
                db.refresh(user_by_email)
                
                dataa = create_permissions_for_user(user_by_email, db)  # Updated line

                token = create_access_token({
                    "email": user_by_email.email,
                    "sub": user_by_email.username,
                    "id": user_by_email.id
                })
                return {
                    "access_token": token,
                    "token_type": "bearer",
                    "user": {
                        "username": user_by_email.username,
                        "id": user_by_email.id,
                        "email": user_by_email.email
                    }
                }

        # Case 2: New user
        else:
            if user_by_oauth:
                raise APIException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="OAuth ID already used by another account."
                )

            new_user = User(
                username=user.username,
                email=user.email,
                role=user.role,
                oAuthId=user.oAuthId
            )
            db.add(new_user)
            dataa = create_permissions_for_user(user_by_email, db)
            db.commit()
            db.refresh(new_user)

            token = create_access_token({
                "email": new_user.email,
                "sub": new_user.username,
                "id": new_user.id
            })
            return {
                "access_token": token,
                "token_type": "bearer",
                "user": {
                    "username": new_user.username,
                    "id": new_user.id,
                    "email": new_user.email
                }
            }

    except Exception as e:
        raise APIException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error. {str(e)}"
        )
   
# Auth callback
@router.get("/auth")
async def auth(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user = await oauth.google.parse_id_token(request, token)
    return JSONResponse(content={"user": user})

@router.post("/login", response_model=Token)
async def login_for_access_token(login_data: EmailPasswordLogin, db= Depends(get_db)):
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
            token = create_access_token({"email": user.email, "sub": user.username, "id": user.id})

        except JWTError:
            raise APIException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal Server Error. Failed to generate access token."
            )
        
        return {"access_token": token, "token_type": "bearer", "user": {"username": user.username, "id": user.id, "email": user.email}}

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
