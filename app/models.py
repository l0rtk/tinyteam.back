from pydantic import BaseModel, Field, EmailStr,ValidationError
from typing import Optional
from fastapi import Form,HTTPException
from typing_extensions import Annotated

class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    mobile: str = Field(..., min_length=1, max_length=50)
class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserInDB(UserBase):
    id: str
    role: str
    hashed_password: str
    avatar: Optional[str] = None

class User(UserBase):
    id: str
    role: str
    avatar: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[EmailStr] = None

class UserRegistration(UserCreate):
    @classmethod
    def as_form(
        cls,
        username: Annotated[str, Form()],
        email: Annotated[EmailStr, Form()],
        password: Annotated[str, Form()],
        mobile: Annotated[str, Form()]
    ):
        try:
            return cls(
                username=username,
                email=email,
                password=password,
                mobile=mobile
            )
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))