from fastapi import APIRouter, Depends
from ..models import User
from ..auth import get_current_user

router = APIRouter()

@router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user