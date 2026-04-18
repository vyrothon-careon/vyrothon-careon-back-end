from pydantic import BaseModel, ConfigDict, EmailStr
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

class SignupIn(BaseModel):
    email: EmailStr
    password: str

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class AuthOut(BaseModel):
    user_id: int
    email: str
    is_onboarded: bool

class OnboardingIn(BaseModel):
    full_name: str
    age: int
    gender: str
    city: str
    typical_bp_systolic: float
    typical_bp_diastolic: float
    typical_heart_rate: float
    known_diseases: str
    current_medications: str
    emergency_contact_email: EmailStr

class OnboardingOut(OnboardingIn):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)
