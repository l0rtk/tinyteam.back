from typing_extensions import Annotated
from fastapi import APIRouter, Depends, HTTPException, status,Form
from fastapi.security import OAuth2PasswordRequestForm
from ..models import User, UserRegistration
from ..auth import authenticate_user, create_access_token, get_password_hash, get_current_user, verify_password
from ..database import get_db
from datetime import timedelta
from bson import ObjectId
from pydantic import ValidationError

router = APIRouter()

@router.post("/register", response_model=User)
async def register(user_form: Annotated[UserRegistration, Depends(UserRegistration.as_form)]):
    try:
        user = UserRegistration(**user_form.dict())
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    db = get_db()
    db_user = db.users.find_one({"email": user.email})
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    db_user = db.users.find_one({"username": user.username})
    if db_user:
        raise HTTPException(status_code=400, detail="Username already taken")

    db_user = db.users.find_one({"mobile": user.mobile})
    if db_user:
        raise HTTPException(status_code=400, detail="Mobile already registered")

    hashed_password = get_password_hash(user.password)
    user_dict = user.dict()
    user_dict["hashed_password"] = hashed_password
    user_dict.pop("password", None)
    user_dict["role"] = "client"  # Default role
    user_dict["id"] = str(ObjectId())

    db.users.insert_one(user_dict)
    return User(**{k: v for k, v in user_dict.items() if k != "hashed_password"})

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    del user.hashed_password
    return {"access_token": access_token, "token_type": "bearer", "user_data" : user}


@router.post("/change-password")
async def change_password(
    current_password: Annotated[str, Form()],
    new_password: Annotated[str, Form()],
    current_user: User = Depends(get_current_user)
):
    db = get_db()
    user = db.users.find_one({"email": current_user.email})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not verify_password(current_password, user['hashed_password']):
        raise HTTPException(status_code=400, detail="Incorrect current password")
    
    if current_password == new_password:
        raise HTTPException(status_code=400, detail="New password must be different from the current password")
    
    hashed_new_password = get_password_hash(new_password)
    
    db.users.update_one(
        {"email": current_user.email},
        {"$set": {"hashed_password": hashed_new_password}}
    )
    
    return {"message": "Password changed successfully"}