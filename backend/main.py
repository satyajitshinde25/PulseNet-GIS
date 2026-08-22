from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime
import random, requests, os, math, json, sqlite3, re
from dotenv import load_dotenv

# Load .env file automatically (looks in backend/ directory)
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from database import engine, get_db, SQLALCHEMY_DATABASE_URL
import models, schemas
from auth import hash_password, verify_password, create_access_token, get_current_user, require_role
import email_service

# ── Auto-recover corrupted SQLite DB ─────────────────────────────────────────
DB_PATH = SQLALCHEMY_DATABASE_URL.replace("sqlite:///", "")
def _ensure_clean_db():
    if not os.path.exists(DB_PATH):
        return  # fresh start, no DB yet
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA integrity_check")
        conn.close()
    except sqlite3.DatabaseError:
        print(f"[PulseNet] WARNING: Corrupted database detected at '{DB_PATH}'. Deleting and recreating...")
        conn.close()
        os.remove(DB_PATH)
        for ext in ["-shm", "-wal"]:
            p = DB_PATH + ext
            if os.path.exists(p):
                os.remove(p)
        print("[PulseNet] Database reset. A fresh database will be created.")

_ensure_clean_db()

# Create all tables
models.Base.metadata.create_all(bind=engine)

# ── Seed default admin ────────────────────────────────────────────────────────
def _seed_admin():
    from database import SessionLocal
    db = SessionLocal()
    try:
        if not db.query(models.User).filter(models.User.role == "ADMIN").first():
            db.add(models.User(
                email="admin@pulsenet.in",
                hashed_password=hash_password("PulseNet@Admin1"),
                role="ADMIN"
            ))
            db.commit()
            print("[PulseNet] Default admin: admin@pulsenet.in / PulseNet@Admin1")
    finally:
        db.close()

_seed_admin()

app = FastAPI(title="PulseNet-GIS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── OSRM / Haversine helper ───────────────────────────────────────────────────
def get_osrm_route(lat1, lon1, lat2, lon2):
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("routes"):
                route = data["routes"][0]
                return {"distance_km": round(route["distance"] / 1000.0, 1),
                        "duration_min": round(route["duration"] / 60.0)}
    except Exception as e:
        print(f"OSRM failed: {e}")

    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    dist = R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return {"distance_km": round(dist, 1), "duration_min": round(dist * 2.5)}


def _hospital_to_dict(h: models.Hospital):
    inv = h.inventory
    return {
        "id": h.id,
        "name": h.name,
        "address": h.address,
        "hospital_phone": h.hospital_phone,
        "emergency_phone": h.emergency_phone,
        "location": {"lat": h.lat, "lng": h.lng},
        "opening_time": h.opening_time,
        "closing_time": h.closing_time,
        "accepting": h.accepting,
        "inventory": {
            "icu": inv.icu if inv else 0,
            "ventilator": inv.ventilator if inv else 0,
            "general": inv.general if inv else 0,
            "blood": inv.blood if inv else 0,
        }
    }


def _phc_to_dict(p: models.PHC):
    return {
        "id": p.id,
        "name": p.name,
        "doctor_name": p.doctor_name,
        "address": p.address,
        "phc_phone": p.phc_phone,
        "doctor_phone": p.doctor_phone,
        "opening_time": p.opening_time,
        "closing_time": p.closing_time,
        "location": {"lat": p.lat, "lng": p.lng},
    }


def _ambulance_to_dict(a: models.Ambulance):
    return {
        "id": a.id,
        "driverName": a.driver_name,
        "driverPhone": a.driver_phone,
        "plate": a.ambulance_no,
        "location": {"lat": a.lat, "lng": a.lng},
        "status": a.status,
    }


def _referral_to_dict(r: models.Referral):
    return {
        "id": r.id,
        "phcId": r.phc_id,
        "patientId": r.patient_id,
        "age": r.age,
        "gender": r.gender,
        "bloodGroup": r.blood_group,
        "condition": r.condition,
        "severity": r.severity,
        "resources": json.loads(r.resources) if r.resources else {},
        "status": r.status,
        "selectedHospitalId": r.selected_hospital_id,
        "ambulanceId": r.ambulance_id,
        "dispatch_queue": json.loads(r.dispatch_queue) if r.dispatch_queue else [],
        "dispatch_expires_at": r.dispatch_expires_at,
        "current_ambulance_index": r.current_ambulance_index,
        "createdAt": r.created_at.isoformat() if r.created_at else None,
        "updatedAt": r.updated_at.isoformat() if r.updated_at else None,
    }


# ── AUTH ROUTES ───────────────────────────────────────────────────────────────

@app.post("/api/v1/auth/register/phc")
def register_phc(data: schemas.RegisterPHC, db: Session = Depends(get_db)):
    # Check no duplicate pending or active email
    if db.query(models.User).filter(models.User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    existing_req = db.query(models.RegistrationRequest).filter(
        models.RegistrationRequest.email == data.email,
        models.RegistrationRequest.status == "PENDING"
    ).first()
    if existing_req:
        raise HTTPException(status_code=400, detail="A pending registration already exists for this email")

    # Remove password from JSON data
    data_dict = data.dict()
    data_dict.pop("password", None)

    req = models.RegistrationRequest(
        role="PHC", email=data.email,
        hashed_password=hash_password(data.password),
        status="PENDING",
        data_json=json.dumps(data_dict)
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    email_service.notify_admin_new_registration("PHC", data.name, data.email, req.id)
    return {"success": True, "message": "Registration submitted for admin approval. You will receive your credentials by email once approved."}


@app.post("/api/v1/auth/register/hospital")
def register_hospital(data: schemas.RegisterHospital, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    existing_req = db.query(models.RegistrationRequest).filter(
        models.RegistrationRequest.email == data.email,
        models.RegistrationRequest.status == "PENDING"
    ).first()
    if existing_req:
        raise HTTPException(status_code=400, detail="A pending registration already exists for this email")

    # Remove password from JSON data
    data_dict = data.dict()
    data_dict.pop("password", None)

    req = models.RegistrationRequest(
        role="HOSPITAL", email=data.email,
        hashed_password=hash_password(data.password),
        status="PENDING",
        data_json=json.dumps(data_dict)
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    email_service.notify_admin_new_registration("HOSPITAL", data.name, data.email, req.id)
    return {"success": True, "message": "Registration submitted for admin approval. You will receive your credentials by email once approved."}


@app.post("/api/v1/auth/register/ambulance")
def register_ambulance(data: schemas.RegisterAmbulance, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    existing_req = db.query(models.RegistrationRequest).filter(
        models.RegistrationRequest.email == data.email,
        models.RegistrationRequest.status == "PENDING"
    ).first()
    if existing_req:
        raise HTTPException(status_code=400, detail="A pending registration already exists for this email")
    if db.query(models.Ambulance).filter(models.Ambulance.ambulance_no == data.ambulance_no).first():
        raise HTTPException(status_code=400, detail="Ambulance number already registered")

    # Remove password from JSON data
    data_dict = data.dict()
    data_dict.pop("password", None)

    req = models.RegistrationRequest(
        role="AMBULANCE", email=data.email,
        hashed_password=hash_password(data.password),
        status="PENDING",
        data_json=json.dumps(data_dict)
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    email_service.notify_admin_new_registration("AMBULANCE", data.driver_name, data.email, req.id)
    return {"success": True, "message": "Registration submitted for admin approval. You will receive your credentials by email once approved."}


# ── ADMIN AUTH ────────────────────────────────────────────────────────────────

@app.post("/admin/api/login")
def admin_login(data: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(
        models.User.email == data.email,
        models.User.role == "ADMIN"
    ).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid admin credentials")
    token = create_access_token({"sub": str(user.id), "role": "ADMIN", "entity_id": None})
    return {"access_token": token, "token_type": "bearer", "role": "ADMIN", "name": "Administrator"}


# ── ADMIN ROUTES ──────────────────────────────────────────────────────────────

@app.get("/admin/api/users")
def admin_get_users(db: Session = Depends(get_db), current_user: models.User = Depends(require_role("ADMIN"))):
    users = db.query(models.User).filter(models.User.role != "ADMIN").all()
    data = []
    for u in users:
        item = {"id": u.id, "email": u.email, "role": u.role, "created_at": u.created_at.isoformat()}
        if u.role == "PHC" and u.phc:
            item["name"] = u.phc.name
        elif u.role == "HOSPITAL" and u.hospital:
            item["name"] = u.hospital.name
        elif u.role == "AMBULANCE" and u.ambulance:
            item["name"] = f"Driver: {u.ambulance.driver_name} ({u.ambulance.ambulance_no})"
        else:
            item["name"] = "Unknown"
        data.append(item)
    return {"success": True, "data": data}


@app.delete("/admin/api/users/{user_id}")
def admin_delete_user(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(require_role("ADMIN"))):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    if user.role == "ADMIN":
        raise HTTPException(400, "Cannot delete admin users")
    db.delete(user)
    db.commit()
    return {"success": True, "message": "User and associated data permanently revoked."}


@app.get("/admin/api/registrations")
def admin_get_registrations(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("ADMIN"))
):
    q = db.query(models.RegistrationRequest)
    if status:
        q = q.filter(models.RegistrationRequest.status == status.upper())
    reqs = q.order_by(models.RegistrationRequest.submitted_at.desc()).all()
    return {"success": True, "data": [
        {
            "id": r.id, "role": r.role, "email": r.email,
            "status": r.status, "submitted_at": r.submitted_at.isoformat(),
            "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
            "admin_note": r.admin_note,
            "data": json.loads(r.data_json)
        } for r in reqs
    ]}


@app.post("/admin/api/registrations/{req_id}/approve")
def admin_approve(req_id: int, payload: dict = {}, db: Session = Depends(get_db),
                  current_user: models.User = Depends(require_role("ADMIN"))):
    req = db.query(models.RegistrationRequest).filter(models.RegistrationRequest.id == req_id).first()
    if not req:
        raise HTTPException(404, "Registration request not found")
    if req.status != "PENDING":
        raise HTTPException(400, f"Request is already {req.status}")

    data = json.loads(req.data_json)

    # Create the actual User + entity using the original hashed password
    user = models.User(email=req.email, hashed_password=req.hashed_password, role=req.role)
    db.add(user)
    db.flush()

    if req.role == "PHC":
        entity = models.PHC(
            user_id=user.id, name=data["name"], doctor_name=data["doctor_name"],
            address=data["address"], phc_phone=data["phc_phone"], doctor_phone=data["doctor_phone"],
            opening_time=data["opening_time"], closing_time=data["closing_time"],
            lat=data["lat"], lng=data["lng"]
        )
        db.add(entity)
        display_name = data["name"]

    elif req.role == "HOSPITAL":
        entity = models.Hospital(
            user_id=user.id, name=data["name"], address=data["address"],
            hospital_phone=data.get("hospital_phone"), emergency_phone=data.get("emergency_phone"),
            lat=data["lat"], lng=data["lng"],
            opening_time=data.get("opening_time"), closing_time=data.get("closing_time"),
            accepting=True
        )
        db.add(entity)
        db.flush()
        inv = models.HospitalInventory(hospital_id=entity.id, icu=0, ventilator=0, general=0, blood=0)
        db.add(inv)
        display_name = data["name"]

    elif req.role == "AMBULANCE":
        entity = models.Ambulance(
            user_id=user.id, driver_name=data["driver_name"], driver_phone=data["driver_phone"],
            ambulance_no=data["ambulance_no"], status="OFFLINE"
        )
        db.add(entity)
        display_name = data["driver_name"]

    req.status = "APPROVED"
    req.reviewed_at = datetime.utcnow()
    req.admin_note = payload.get("note", "")
    db.commit()

    # Send credentials email
    email_service.send_approval_credentials(req.email, display_name, req.role, req.email)
    return {"success": True, "message": f"{req.role} approved. Credentials emailed to {req.email}."}


@app.post("/admin/api/registrations/{req_id}/reject")
def admin_reject(req_id: int, payload: dict = {}, db: Session = Depends(get_db),
                 current_user: models.User = Depends(require_role("ADMIN"))):
    req = db.query(models.RegistrationRequest).filter(models.RegistrationRequest.id == req_id).first()
    if not req:
        raise HTTPException(404, "Registration request not found")
    if req.status != "PENDING":
        raise HTTPException(400, f"Request is already {req.status}")

    data = json.loads(req.data_json)
    display_name = data.get("name") or data.get("driver_name", "User")
    reason = payload.get("reason", "")

    req.status = "REJECTED"
    req.reviewed_at = datetime.utcnow()
    req.admin_note = reason
    db.commit()

    email_service.send_rejection_email(req.email, display_name, req.role, reason)
    return {"success": True, "message": "Registration rejected and applicant notified."}


@app.get("/admin/api/stats")
def admin_stats(db: Session = Depends(get_db),
               current_user: models.User = Depends(require_role("ADMIN"))):
    pending = db.query(models.RegistrationRequest).filter(models.RegistrationRequest.status == "PENDING").count()
    approved = db.query(models.RegistrationRequest).filter(models.RegistrationRequest.status == "APPROVED").count()
    rejected = db.query(models.RegistrationRequest).filter(models.RegistrationRequest.status == "REJECTED").count()
    phcs = db.query(models.PHC).count()
    hospitals = db.query(models.Hospital).count()
    ambulances = db.query(models.Ambulance).count()
    return {"success": True, "data": {
        "pending": pending, "approved": approved, "rejected": rejected,
        "phcs": phcs, "hospitals": hospitals, "ambulances": ambulances
    }}


@app.post("/api/v1/auth/login")
def login(data: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == data.email).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    # Get the entity ID linked to this user
    entity_id = None
    extra = {}
    if user.role == "PHC" and user.phc:
        entity_id = user.phc.id
        extra = {"phcId": user.phc.id, "name": user.phc.name, "doctorName": user.phc.doctor_name}
    elif user.role == "HOSPITAL" and user.hospital:
        entity_id = user.hospital.id
        extra = {"hospitalId": user.hospital.id, "name": user.hospital.name}
    elif user.role == "AMBULANCE" and user.ambulance:
        entity_id = user.ambulance.id
        extra = {"ambulanceId": user.ambulance.id, "driverName": user.ambulance.driver_name,
                 "plate": user.ambulance.ambulance_no}
        # Set ambulance to AVAILABLE on login
        user.ambulance.status = "AVAILABLE"
        db.commit()

    token = create_access_token({"sub": str(user.id), "role": user.role, "entity_id": entity_id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "entity_id": entity_id,
        **extra
    }


@app.get("/api/v1/auth/me")
def get_me(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = {"id": current_user.id, "email": current_user.email, "role": current_user.role}
    if current_user.role == "PHC" and current_user.phc:
        data.update(_phc_to_dict(current_user.phc))
    elif current_user.role == "HOSPITAL" and current_user.hospital:
        data.update(_hospital_to_dict(current_user.hospital))
    elif current_user.role == "AMBULANCE" and current_user.ambulance:
        data.update(_ambulance_to_dict(current_user.ambulance))
    return {"success": True, "data": data}


# ── PHC ROUTES ────────────────────────────────────────────────────────────────

@app.get("/api/v1/phcs")
def get_phcs(db: Session = Depends(get_db)):
    phcs = db.query(models.PHC).all()
    return {"success": True, "data": [_phc_to_dict(p) for p in phcs]}


@app.get("/api/v1/phcs/{phc_id}")
def get_phc(phc_id: int, db: Session = Depends(get_db)):
    p = db.query(models.PHC).filter(models.PHC.id == phc_id).first()
    if not p:
        raise HTTPException(404, "PHC not found")
    return {"success": True, "data": _phc_to_dict(p)}


# ── HOSPITAL ROUTES ───────────────────────────────────────────────────────────

@app.get("/api/v1/hospitals")
def get_hospitals(db: Session = Depends(get_db)):
    hospitals = db.query(models.Hospital).all()
    return {"success": True, "data": [_hospital_to_dict(h) for h in hospitals]}


@app.get("/api/v1/hospitals/{hospital_id}/inventory")
def get_hospital_inventory(hospital_id: int, db: Session = Depends(get_db)):
    h = db.query(models.Hospital).filter(models.Hospital.id == hospital_id).first()
    if not h:
        raise HTTPException(404, "Hospital not found")
    inv = h.inventory
    return {"success": True, "data": {
        "icu": inv.icu if inv else 0, "ventilator": inv.ventilator if inv else 0,
        "general": inv.general if inv else 0, "blood": inv.blood if inv else 0
    }}


@app.put("/api/v1/hospitals/{hospital_id}/inventory")
def update_hospital_inventory(hospital_id: int, data: schemas.InventoryUpdate,
                               db: Session = Depends(get_db),
                               current_user: models.User = Depends(require_role("HOSPITAL"))):
    h = db.query(models.Hospital).filter(models.Hospital.id == hospital_id).first()
    if not h:
        raise HTTPException(404, "Hospital not found")
    if h.user_id != current_user.id:
        raise HTTPException(403, "You can only update your own hospital")
    inv = h.inventory
    if not inv:
        inv = models.HospitalInventory(hospital_id=hospital_id)
        db.add(inv)
    if data.icu is not None: inv.icu = max(0, data.icu)
    if data.ventilator is not None: inv.ventilator = max(0, data.ventilator)
    if data.general is not None: inv.general = max(0, data.general)
    if data.blood is not None: inv.blood = max(0, data.blood)
    db.commit()
    db.refresh(inv)
    return {"success": True, "data": {"icu": inv.icu, "ventilator": inv.ventilator,
                                       "general": inv.general, "blood": inv.blood}}


# ── AMBULANCE ROUTES ──────────────────────────────────────────────────────────

@app.get("/api/v1/ambulances")
def get_ambulances(db: Session = Depends(get_db)):
    ambulances = db.query(models.Ambulance).all()
    return {"success": True, "data": [_ambulance_to_dict(a) for a in ambulances]}


@app.put("/api/v1/ambulances/{ambulance_id}/status")
def update_ambulance_status(ambulance_id: int, data: schemas.AmbulanceStatusUpdate,
                             db: Session = Depends(get_db)):
    a = db.query(models.Ambulance).filter(models.Ambulance.id == ambulance_id).first()
    if not a:
        raise HTTPException(404, "Ambulance not found")
    a.status = data.status
    db.commit()
    return {"success": True, "data": _ambulance_to_dict(a)}


@app.put("/api/v1/ambulances/location")
def update_ambulance_location(data: schemas.AmbulanceLocationUpdate,
                               db: Session = Depends(get_db),
                               current_user: models.User = Depends(require_role("AMBULANCE"))):
    a = current_user.ambulance
    if not a:
        raise HTTPException(404, "Ambulance not found for this user")
    a.lat = data.lat
    a.lng = data.lng
    # Auto set AVAILABLE if it was OFFLINE (first GPS ping after login)
    if a.status == "OFFLINE":
        a.status = "AVAILABLE"
    db.commit()
    return {"success": True, "data": {"lat": a.lat, "lng": a.lng, "status": a.status}}


@app.get("/api/v1/ambulances/{ambulance_id}/alert")
def check_ambulance_alert(ambulance_id: int, db: Session = Depends(get_db)):
    now = datetime.utcnow().timestamp()
    referrals = db.query(models.Referral).filter(models.Referral.status == "ACCEPTED").all()
    for ref in referrals:
        if not ref.dispatch_queue:
            continue
        if now > (ref.dispatch_expires_at or 0):
            ref.current_ambulance_index = (ref.current_ambulance_index or 0) + 1
            ref.dispatch_expires_at = now + 15
            db.commit()
        idx = ref.current_ambulance_index or 0
        queue = json.loads(ref.dispatch_queue)
        if idx < len(queue) and queue[idx] == ambulance_id:
            return {"success": True, "data": _referral_to_dict(ref)}
    return {"success": False, "message": "No active alert"}


# ── MATCHING & RESERVATIONS ───────────────────────────────────────────────────

@app.post("/api/v1/matching")
def get_matching_hospitals(requirements: Dict[str, Any], db: Session = Depends(get_db)):
    phc_id = requirements.get("phcId")
    phc = db.query(models.PHC).filter(models.PHC.id == phc_id).first()
    if not phc:
        raise HTTPException(404, "PHC not found")

    hospitals = db.query(models.Hospital).all()
    matched, rejected = [], []

    for h in hospitals:
        inv = h.inventory
        reasons = []
        if not h.accepting:
            reasons.append("Hospital not accepting emergencies")
        if requirements.get("icu") and (not inv or inv.icu <= 0):
            reasons.append("ICU unavailable")
        if requirements.get("ventilator") and (not inv or inv.ventilator <= 0):
            reasons.append("Ventilator unavailable")
        if requirements.get("blood") and (not inv or inv.blood < requirements.get("bloodUnits", 1)):
            reasons.append(f"Insufficient blood units")
        if reasons:
            rejected.append({"hospital": h.name, "reasons": reasons})
            continue
        route = get_osrm_route(phc.lat, phc.lng, h.lat, h.lng)
        entry = _hospital_to_dict(h)
        entry["distanceKm"] = route["distance_km"]
        entry["etaMin"] = route["duration_min"]
        matched.append(entry)

    matched.sort(key=lambda x: x["etaMin"])
    return {"success": True, "data": matched, "rejected": rejected,
            "phc_loc": {"lat": phc.lat, "lng": phc.lng}}


@app.post("/api/v1/reservations")
def lock_resources(data: dict, db: Session = Depends(get_db)):
    hospital_id = data.get("hospitalId")
    h = db.query(models.Hospital).filter(models.Hospital.id == hospital_id).first()
    if not h:
        raise HTTPException(404, "Hospital not found")
    inv = h.inventory
    reqs = data.get("resources", {})
    for key, req_val in reqs.items():
        if req_val and hasattr(inv, key):
            qty = 1 if type(req_val) == bool else req_val
            if getattr(inv, key) < qty:
                return {"success": False, "message": f"Conflict: {key} no longer available"}
    for key, req_val in reqs.items():
        if req_val and hasattr(inv, key):
            qty = 1 if type(req_val) == bool else req_val
            setattr(inv, key, getattr(inv, key) - qty)
    db.commit()
    return {"success": True, "message": "Resources locked", "expiresIn": "04:32"}


# ── REFERRAL ROUTES ───────────────────────────────────────────────────────────

@app.post("/api/v1/referrals")
def create_referral(data: schemas.ReferralCreate, db: Session = Depends(get_db)):
    phc = db.query(models.PHC).filter(models.PHC.id == data.phcId).first()
    if not phc:
        raise HTTPException(404, "PHC not found")
    ref_id = f"REF-{random.randint(1000, 9999)}"
    referral = models.Referral(
        id=ref_id, phc_id=data.phcId, patient_id=data.patientId,
        age=data.age, gender=data.gender, blood_group=data.bloodGroup,
        condition=data.condition, severity=data.severity,
        resources=json.dumps(data.resources), status="PENDING_MATCHING",
        require_ambulance=data.requireAmbulance
    )
    db.add(referral)
    db.commit()
    db.refresh(referral)
    return {"success": True, "data": _referral_to_dict(referral)}


@app.get("/api/v1/referrals")
def get_all_referrals(db: Session = Depends(get_db)):
    refs = db.query(models.Referral).all()
    return {"success": True, "data": [_referral_to_dict(r) for r in refs]}


@app.get("/api/v1/referrals/{referral_id}")
def get_referral(referral_id: str, db: Session = Depends(get_db)):
    ref = db.query(models.Referral).filter(models.Referral.id == referral_id).first()
    if not ref:
        raise HTTPException(404, "Not found")
    return {"success": True, "data": _referral_to_dict(ref)}


@app.put("/api/v1/referrals/{referral_id}/status")
def update_referral_status(referral_id: str, data: schemas.ReferralUpdateStatus,
                            db: Session = Depends(get_db)):
    ref = db.query(models.Referral).filter(models.Referral.id == referral_id).first()
    if not ref:
        raise HTTPException(404, "Not found")

    ref.status = data.status
    extra = data.extraData or {}
    if "selectedHospitalId" in extra:
        ref.selected_hospital_id = extra["selectedHospitalId"]

    # Dispatch cascade on ACCEPTED
    if data.status == "ACCEPTED":
        if not ref.require_ambulance:
            # Bypass ambulance dispatch completely
            ref.status = "ACCEPTED_SELF_TRANSPORT"
        else:
            phc = ref.phc
            ambulances = db.query(models.Ambulance).filter(models.Ambulance.status == "AVAILABLE",
                                                            models.Ambulance.lat != None).all()
            available = []
            for a in ambulances:
                rt = get_osrm_route(a.lat, a.lng, phc.lat, phc.lng)
                available.append({"id": a.id, "etaMin": rt["duration_min"]})
            available.sort(key=lambda x: x["etaMin"])
            ref.dispatch_queue = json.dumps([a["id"] for a in available])
            ref.current_ambulance_index = 0
            ref.dispatch_expires_at = datetime.utcnow().timestamp() + 15 if available else 0

    # Restore inventory on rejection
    if data.status == "REJECTED_BY_HOSPITAL" and ref.selected_hospital_id:
        h = db.query(models.Hospital).filter(models.Hospital.id == ref.selected_hospital_id).first()
        if h and h.inventory:
            reqs = json.loads(ref.resources) if ref.resources else {}
            inv = h.inventory
            for key, req_val in reqs.items():
                if req_val and hasattr(inv, key):
                    qty = 1 if type(req_val) == bool else req_val
                    setattr(inv, key, getattr(inv, key) + qty)

    ref.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(ref)
    return {"success": True, "data": _referral_to_dict(ref)}


@app.post("/api/v1/referrals/{referral_id}/accept_dispatch")
def accept_dispatch(referral_id: str, payload: dict, db: Session = Depends(get_db)):
    ref = db.query(models.Referral).filter(models.Referral.id == referral_id).first()
    if not ref:
        raise HTTPException(404, "Not found")
    ambulance_id = payload.get("ambulanceId")
    ref.status = "AMBULANCE_DISPATCHED"
    ref.ambulance_id = ambulance_id
    a = db.query(models.Ambulance).filter(models.Ambulance.id == ambulance_id).first()
    if a:
        a.status = "BUSY"
    db.commit()
    return {"success": True, "data": _referral_to_dict(ref)}


@app.post("/api/v1/referrals/{referral_id}/decline_dispatch")
def decline_dispatch(referral_id: str, payload: dict, db: Session = Depends(get_db)):
    ref = db.query(models.Referral).filter(models.Referral.id == referral_id).first()
    if not ref:
        raise HTTPException(404, "Not found")
    ref.current_ambulance_index = (ref.current_ambulance_index or 0) + 1
    ref.dispatch_expires_at = datetime.utcnow().timestamp() + 15
    db.commit()
    return {"success": True}


# ── NETWORK MAP ───────────────────────────────────────────────────────────────

@app.get("/api/v1/network")
def get_network_data(db: Session = Depends(get_db)):
    return {
        "success": True,
        "data": {
            "hospitals": [_hospital_to_dict(h) for h in db.query(models.Hospital).all()],
            "phcs": [_phc_to_dict(p) for p in db.query(models.PHC).all()],
            "ambulances": [_ambulance_to_dict(a) for a in db.query(models.Ambulance).all()],
        }
    }


# ── STATIC FILES ──────────────────────────────────────────────────────────────
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "pulsenet-gis-frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
