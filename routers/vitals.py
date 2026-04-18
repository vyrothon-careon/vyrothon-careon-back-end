from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import asc
from typing import List
from datetime import datetime, timedelta

from database import get_db
import models
import schemas

router = APIRouter(tags=["vitals"])

@router.get("/patients", response_model=List[schemas.PatientOut])
async def list_patients(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Patient))
    return result.scalars().all()

@router.post("/patients", response_model=schemas.PatientOut)
async def create_patient(patient: schemas.PatientCreate, db: AsyncSession = Depends(get_db)):
    new_patient = models.Patient(name=patient.name, age=patient.age)
    db.add(new_patient)
    await db.commit()
    await db.refresh(new_patient)
    return new_patient

@router.post("/vitals", response_model=dict)
async def create_vital(
    vital: schemas.VitalIn, 
    patient_id: int = Query(..., description="Patient ID"), 
    db: AsyncSession = Depends(get_db)
):
    patient = await db.get(models.Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    new_vital = models.VitalReading(
        patient_id=patient_id,
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

@router.get("/patient/{id}/history", response_model=List[schemas.VitalOut])
async def patient_history(id: int, days: int = Query(7), db: AsyncSession = Depends(get_db)):
    patient = await db.get(models.Patient, id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    cutoff_date = datetime.now() - timedelta(days=days)
    stmt = (
        select(models.VitalReading)
        .where(models.VitalReading.patient_id == id)
        .where(models.VitalReading.date >= cutoff_date)
        .order_by(asc(models.VitalReading.date))
    )
    result = await db.execute(stmt)
    return result.scalars().all()
