from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False)  # PHC | HOSPITAL | AMBULANCE | ADMIN
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    phc = relationship("PHC", back_populates="user", uselist=False, cascade="all, delete")
    hospital = relationship("Hospital", back_populates="user", uselist=False, cascade="all, delete")
    ambulance = relationship("Ambulance", back_populates="user", uselist=False, cascade="all, delete")


class RegistrationRequest(Base):
    """Holds pending registrations awaiting admin approval."""
    __tablename__ = "registration_requests"
    id = Column(Integer, primary_key=True, index=True)
    role = Column(String, nullable=False)          # PHC | HOSPITAL | AMBULANCE
    email = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    status = Column(String, default="PENDING")     # PENDING | APPROVED | REJECTED
    data_json = Column(Text, nullable=False)       # All form data serialized as JSON
    submitted_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
    admin_note = Column(String, nullable=True)


class PHC(Base):
    __tablename__ = "phcs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    name = Column(String, nullable=False)
    doctor_name = Column(String, nullable=False)
    address = Column(Text, nullable=False)
    phc_phone = Column(String, nullable=False)
    doctor_phone = Column(String, nullable=False)
    opening_time = Column(String, nullable=False)
    closing_time = Column(String, nullable=False)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)

    user = relationship("User", back_populates="phc")
    referrals = relationship("Referral", back_populates="phc")


class Hospital(Base):
    __tablename__ = "hospitals"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    name = Column(String, nullable=False)
    address = Column(Text, nullable=False)
    hospital_phone = Column(String, nullable=True)
    emergency_phone = Column(String, nullable=True)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    opening_time = Column(String, nullable=True)
    closing_time = Column(String, nullable=True)
    accepting = Column(Boolean, default=True)

    user = relationship("User", back_populates="hospital")
    inventory = relationship("HospitalInventory", back_populates="hospital", uselist=False)


class HospitalInventory(Base):
    __tablename__ = "hospital_inventories"
    id = Column(Integer, primary_key=True, index=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), unique=True)
    icu = Column(Integer, default=0)
    ventilator = Column(Integer, default=0)
    general = Column(Integer, default=0)
    blood = Column(Integer, default=0)

    hospital = relationship("Hospital", back_populates="inventory")


class Ambulance(Base):
    __tablename__ = "ambulances"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    driver_name = Column(String, nullable=False)
    driver_phone = Column(String, nullable=False)
    ambulance_no = Column(String, nullable=False, unique=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    status = Column(String, default="OFFLINE")

    user = relationship("User", back_populates="ambulance")


class Referral(Base):
    __tablename__ = "referrals"
    id = Column(String, primary_key=True, index=True)
    phc_id = Column(Integer, ForeignKey("phcs.id"), nullable=False)
    patient_id = Column(String, nullable=False)
    age = Column(Integer)
    gender = Column(String)
    blood_group = Column(String)
    condition = Column(Text)
    severity = Column(String)
    resources = Column(Text)
    status = Column(String, default="PENDING_MATCHING")
    require_ambulance = Column(Boolean, default=True)
    selected_hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=True)
    ambulance_id = Column(Integer, ForeignKey("ambulances.id"), nullable=True)
    dispatch_queue = Column(Text, nullable=True)
    dispatch_expires_at = Column(Float, nullable=True)
    current_ambulance_index = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    phc = relationship("PHC", back_populates="referrals")
    selected_hospital = relationship("Hospital", foreign_keys=[selected_hospital_id])
    ambulance = relationship("Ambulance", foreign_keys=[ambulance_id])
