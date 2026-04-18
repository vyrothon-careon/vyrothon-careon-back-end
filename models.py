from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
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
