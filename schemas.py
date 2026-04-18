from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class VitalIn(BaseModel):
    bp_systolic: float
    bp_diastolic: float
    sugar: float
    heart_rate: float
    weight: Optional[float] = None

class VitalOut(VitalIn):
    id: int
    date: datetime

    model_config = ConfigDict(from_attributes=True)

class PatientCreate(BaseModel):
    name: str
    age: int

class PatientOut(PatientCreate):
    id: int

    model_config = ConfigDict(from_attributes=True)
