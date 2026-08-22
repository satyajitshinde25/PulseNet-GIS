from pydantic import BaseModel, EmailStr, validator
from typing import Optional


# ── Password rule helper ──────────────────────────────────────────────────────
def validate_password(v: str) -> str:
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    if not any(c.isupper() for c in v):
        raise ValueError("Password must contain at least one uppercase letter.")
    if not any(c.isdigit() for c in v):
        raise ValueError("Password must contain at least one digit.")
    if not any(c in "!@#$%^&*()-_=+[]{}|;:',.<>?/" for c in v):
        raise ValueError("Password must contain at least one special character.")
    return v


# ── Auth ──────────────────────────────────────────────────────────────────────
class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    entity_id: int


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ── Registration ──────────────────────────────────────────────────────────────
class RegisterPHC(BaseModel):
    email: EmailStr
    password: str
    name: str
    doctor_name: str
    address: str
    phc_phone: str
    doctor_phone: str
    opening_time: str
    closing_time: str
    lat: float
    lng: float

    @validator("password")
    def password_strength(cls, v):
        return validate_password(v)


class RegisterHospital(BaseModel):
    email: EmailStr
    password: str
    name: str
    hospital_phone: str
    emergency_phone: str
    opening_time: str
    closing_time: str
    address: str
    lat: float
    lng: float

    @validator("password")
    def password_strength(cls, v):
        return validate_password(v)


class RegisterAmbulance(BaseModel):
    email: EmailStr
    password: str
    driver_name: str
    driver_phone: str
    ambulance_no: str

    @validator("password")
    def password_strength(cls, v):
        return validate_password(v)


# ── Operational Schemas ───────────────────────────────────────────────────────
class InventoryUpdate(BaseModel):
    icu: Optional[int] = None
    ventilator: Optional[int] = None
    general: Optional[int] = None
    blood: Optional[int] = None


class AmbulanceLocationUpdate(BaseModel):
    lat: float
    lng: float


class AmbulanceStatusUpdate(BaseModel):
    status: str


class ReferralCreate(BaseModel):
    patientId: str
    age: int
    gender: str
    bloodGroup: str
    condition: str
    severity: str
    resources: dict
    phcId: int
    requireAmbulance: bool = True


class ReferralUpdateStatus(BaseModel):
    status: str
    extraData: Optional[dict] = {}
