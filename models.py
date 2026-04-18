from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    age = Column(Integer)

    vitals = relationship("VitalReading", back_populates="patient", cascade="all, delete-orphan")

class VitalReading(Base):
    __tablename__ = "vital_readings"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    date = Column(DateTime, default=datetime.now)
    bp_systolic = Column(Float)
    bp_diastolic = Column(Float)
    sugar = Column(Float)
    heart_rate = Column(Float)
    weight = Column(Float, nullable=True)

    patient = relationship("Patient", back_populates="vitals")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_onboarded = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

class HealthProfile(Base):
    __tablename__ = "health_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    full_name = Column(String)
    age = Column(Integer)
    gender = Column(String)
    city = Column(String)
    typical_bp_systolic = Column(Float)
    typical_bp_diastolic = Column(Float)
    typical_heart_rate = Column(Float)
    known_diseases = Column(String)
    current_medications = Column(String)
    emergency_contact_email = Column(String)
