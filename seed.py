import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database import AsyncSessionLocal
import models

async def seed_data():
    async with AsyncSessionLocal() as session:
        # Check if patient exists
        result = await session.execute(select(models.Patient).where(models.Patient.id == 1))
        existing_patient = result.scalar_one_or_none()

        if existing_patient:
            vitals_result = await session.execute(
                select(models.VitalReading).where(models.VitalReading.patient_id == 1)
            )
            vitals = vitals_result.scalars().all()
            if vitals:
                print("Patient ID 1 already has readings. Skipping seed.")
                return

        if not existing_patient:
            print("Creating demo patient...")
            patient = models.Patient(id=1, name="Ahmad Raza", age=52)
            session.add(patient)
            await session.commit()
            print("Demo patient created.")

        readings = [
            {"bp_systolic":125,"bp_diastolic":82,"sugar":105,"heart_rate":72,"weight":82.0},
            {"bp_systolic":130,"bp_diastolic":85,"sugar":115,"heart_rate":75,"weight":82.2},
            {"bp_systolic":138,"bp_diastolic":88,"sugar":128,"heart_rate":78,"weight":82.5},
            {"bp_systolic":145,"bp_diastolic":92,"sugar":138,"heart_rate":80,"weight":82.8},
            {"bp_systolic":152,"bp_diastolic":95,"sugar":145,"heart_rate":82,"weight":83.1},
            {"bp_systolic":158,"bp_diastolic":98,"sugar":155,"heart_rate":84,"weight":83.4},
            {"bp_systolic":162,"bp_diastolic":102,"sugar":162,"heart_rate":86,"weight":83.8},
        ]

        print("Seeding vitals readings...")
        base_time = datetime.now()
        for i, val in enumerate(readings):
            # The prompt says: datetime.now() - timedelta(days=6-i) 
            record_date = base_time - timedelta(days=(6 - i))
            vital = models.VitalReading(
                patient_id=1,
                date=record_date,
                **val
            )
            session.add(vital)
        
        await session.commit()
        print("Seed completed successfully.")

if __name__ == "__main__":
    asyncio.run(seed_data())
