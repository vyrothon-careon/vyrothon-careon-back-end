from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import bcrypt

from database import get_db
import models
import schemas

router = APIRouter(prefix="/auth", tags=["auth"])

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

@router.post("/signup", response_model=schemas.AuthOut)
async def signup(user_in: schemas.SignupIn, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.User).where(models.User.email == user_in.email))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    new_user = models.User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        is_onboarded=False
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return schemas.AuthOut(
        user_id=new_user.id,
        email=new_user.email,
        is_onboarded=new_user.is_onboarded
    )

@router.post("/login", response_model=schemas.AuthOut)
async def login(user_in: schemas.LoginIn, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.User).where(models.User.email == user_in.email))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    if not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    return schemas.AuthOut(
        user_id=user.id,
        email=user.email,
        is_onboarded=user.is_onboarded
    )
