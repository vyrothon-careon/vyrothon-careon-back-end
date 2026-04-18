from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database import get_db
import models
import schemas

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

@router.post("", response_model=schemas.OnboardingOut)
async def create_onboarding(
    profile_in: schemas.OnboardingIn,
    user_id: int = Query(...),
    db: AsyncSession = Depends(get_db)
):
    user = await db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if user.is_onboarded:
        raise HTTPException(status_code=400, detail="Already onboarded")
        
    result = await db.execute(select(models.HealthProfile).where(models.HealthProfile.user_id == user_id))
    existing_profile = result.scalar_one_or_none()
    if existing_profile:
        raise HTTPException(status_code=400, detail="Health profile already exists")
        
    new_profile = models.HealthProfile(
        user_id=user_id,
        full_name=profile_in.full_name,
        age=profile_in.age,
        gender=profile_in.gender,
        city=profile_in.city,
        typical_bp_systolic=profile_in.typical_bp_systolic,
        typical_bp_diastolic=profile_in.typical_bp_diastolic,
        typical_heart_rate=profile_in.typical_heart_rate,
        known_diseases=profile_in.known_diseases,
        current_medications=profile_in.current_medications,
        emergency_contact_email=profile_in.emergency_contact_email
    )
    
    db.add(new_profile)
    user.is_onboarded = True
    
    await db.commit()
    await db.refresh(new_profile)
    
    return new_profile

@router.get("/me", response_model=schemas.OnboardingOut)
async def get_my_onboarding(user_id: int = Query(...), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.HealthProfile).where(models.HealthProfile.user_id == user_id))
    profile = result.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
        
    return profile
