from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str = "user" 

class UserOut(BaseModel):
    id: int
    username: str
    role: str

    # class Config:
    #     orm_mode = True
    model_config = {
        "from_attributes": True
    }

class User(BaseModel):
    username: str
    id: int
    email: str
    
class Token(BaseModel):
    access_token: str
    token_type: str
    user: User

