from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import asc
from typing import List
from datetime import datetime, timedelta

from database import get_db
import models
import schemas

router = APIRouter(prefix="/user", tags=["user_vitals"])

@router.post("/vitals", response_model=dict)
async def create_user_vital(
    vital: schemas.UserVitalIn, 
    user_id: int = Query(..., description="User ID"), 
    db: AsyncSession = Depends(get_db)
):
    user = await db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_vital = models.UserVitalReading(
        user_id=user_id,
        bp_systolic=vital.bp_systolic,
        bp_diastolic=vital.bp_diastolic,
        sugar=vital.sugar,
        heart_rate=vital.heart_rate,
        weight=vital.weight
    )
    db.add(new_vital)
    await db.commit()
    await db.refresh(new_vital)
    return {"status": "success", "id": new_vital.id}

@router.get("/{id}/history", response_model=List[schemas.UserVitalOut])
async def user_history(id: int, days: int = Query(7), db: AsyncSession = Depends(get_db)):
    user = await db.get(models.User, id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    cutoff_date = datetime.now() - timedelta(days=days)
    stmt = (
        select(models.UserVitalReading)
        .where(models.UserVitalReading.user_id == id)
        .where(models.UserVitalReading.date >= cutoff_date)
        .order_by(asc(models.UserVitalReading.date))
    )
    result = await db.execute(stmt)
    return result.scalars().all()
