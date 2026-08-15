from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import random
import requests
import os
import asyncio

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- IN-MEMORY DB ---
db_phcs = {
    "phc-1": {"id": "phc-1", "name": "Mulshi Rural PHC", "location": {"lat": 18.5304, "lng": 73.5701}},
    "phc-2": {"id": "phc-2", "name": "Shirur PHC", "location": {"lat": 18.8286, "lng": 74.3730}},
    "phc-3": {"id": "phc-3", "name": "Bhor PHC", "location": {"lat": 18.1636, "lng": 73.8447}},
    "phc-4": {"id": "phc-4", "name": "Khed PHC", "location": {"lat": 18.8471, "lng": 73.8953}},
}

db_hospitals = [
    {
        "id": "hosp-1",
        "name": "Ruby Hall Clinic",
        "location": {"lat": 18.5310, "lng": 73.5750},
        "inventory": {"icu": 5, "ventilator": 3, "general": 10, "blood": 15},
        "specialists": ["Cardiologist", "Neurologist", "Trauma Surgeon"],
        "accepting": True,
        "load": 65
    },
    {
        "id": "hosp-2",
        "name": "Sassoon General Hospital",
        "location": {"lat": 18.5255, "lng": 73.8735},
        "inventory": {"icu": 0, "ventilator": 0, "general": 5, "blood": 30},
        "specialists": ["Trauma Surgeon"],
        "accepting": False,
        "load": 98
    },
    {
        "id": "hosp-3",
        "name": "YCM Hospital, Pimpri",
        "location": {"lat": 18.6253, "lng": 73.8115},
        "inventory": {"icu": 8, "ventilator": 4, "general": 20, "blood": 8},
        "specialists": ["General Surgeon", "Pediatrician"],
        "accepting": True,
        "load": 42
    },
    {
        "id": "hosp-4",
        "name": "Aditya Birla Hospital",
        "location": {"lat": 18.6186, "lng": 73.7712},
        "inventory": {"icu": 3, "ventilator": 1, "general": 12, "blood": 20},
        "specialists": ["Cardiologist", "Pulmonologist"],
        "accepting": True,
        "load": 75
    },
    {
        "id": "hosp-5",
        "name": "Deenanath Mangeshkar Hospital",
        "location": {"lat": 18.4975, "lng": 73.8227},
        "inventory": {"icu": 6, "ventilator": 5, "general": 15, "blood": 25},
        "specialists": ["Neurologist", "Orthopedic Surgeon"],
        "accepting": True,
        "load": 55
    },
    {
        "id": "hosp-6",
        "name": "Jehangir Hospital",
        "location": {"lat": 18.5312, "lng": 73.8765},
        "inventory": {"icu": 2, "ventilator": 0, "general": 8, "blood": 10},
        "specialists": ["Pediatrician", "General Surgeon"],
        "accepting": True,
        "load": 80
    },
]

db_ambulances = [
    {"id": "amb-1", "driverName": "Ramesh K.", "plate": "MH-12-AB-1045", "location": {"lat": 18.5300, "lng": 73.5800}, "status": "AVAILABLE"},
    {"id": "amb-2", "driverName": "Suresh M.", "plate": "MH-12-CD-8821", "location": {"lat": 18.5800, "lng": 73.8200}, "status": "AVAILABLE"},
    {"id": "amb-3", "driverName": "Vijay T.", "plate": "MH-12-EF-7732", "location": {"lat": 18.6100, "lng": 73.8000}, "status": "BUSY"},
    {"id": "amb-4", "driverName": "Prakash D.", "plate": "MH-12-GH-1234", "location": {"lat": 18.5100, "lng": 73.8300}, "status": "AVAILABLE"},
    {"id": "amb-5", "driverName": "Amit R.", "plate": "MH-12-IJ-5678", "location": {"lat": 18.5400, "lng": 73.9000}, "status": "AVAILABLE"}
]

db_referrals = []

# --- OSRM HELPER ---
def get_osrm_route(lat1, lon1, lat2, lon2):
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("routes") and len(data["routes"]) > 0:
                route = data["routes"][0]
                return {
                    "distance_km": round(route["distance"] / 1000.0, 1),
                    "duration_min": round(route["duration"] / 60.0)
                }
    except Exception as e:
        print(f"OSRM Request failed: {e}")
    # Fallback to Haversine if OSRM fails
    import math
    R = 6371  # Radius of earth in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(lat1)) \
        * math.cos(math.radians(lat2)) * math.sin(dlon/2) * math.sin(dlon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    dist = R * c
    return {
        "distance_km": round(dist, 1),
        "duration_min": round(dist * 2.5) # Roughly 40km/h
    }

# --- MODELS ---
class ReferralCreate(BaseModel):
    patientId: str
    age: int
    gender: str
    bloodGroup: str
    condition: str
    severity: str
    resources: Dict[str, Any]
    phcId: str = "phc-1"

class ReferralUpdateStatus(BaseModel):
    status: str
    extraData: Optional[Dict[str, Any]] = {}

class HospitalInventoryUpdate(BaseModel):
    inventory: Dict[str, Any]

class AmbulanceStatusUpdate(BaseModel):
    status: str

# --- ROUTES ---
@app.post("/api/v1/referrals")
def create_referral(data: ReferralCreate):
    new_referral = {
        "id": f"REF-{random.randint(1000, 9999)}",
        "createdAt": datetime.utcnow().isoformat(),
        "status": "PENDING_MATCHING",
        **data.dict()
    }
    db_referrals.append(new_referral)
    return {"success": True, "data": new_referral}

@app.get("/api/v1/referrals/{referral_id}")
def get_referral(referral_id: str):
    ref = next((r for r in db_referrals if r["id"] == referral_id), None)
    if not ref:
        return {"success": False, "message": "Not found"}
    return {"success": True, "data": ref}

@app.get("/api/v1/referrals")
def get_all_referrals():
    return {"success": True, "data": db_referrals}

@app.put("/api/v1/referrals/{referral_id}/status")
def update_referral_status(referral_id: str, data: ReferralUpdateStatus):
    ref = next((r for r in db_referrals if r["id"] == referral_id), None)
    if not ref:
        return {"success": False, "message": "Not found"}
    
    ref["status"] = data.status
    if data.extraData:
        for k, v in data.extraData.items():
            ref[k] = v
            
    # Cascade logic for Ambulance Dispatch
    if data.status == "ACCEPTED":
        phc_loc = db_phcs[ref["phcId"]]["location"]
        available_ambs = []
        for a in db_ambulances:
            if a["status"] == "AVAILABLE":
                rt = get_osrm_route(a["location"]["lat"], a["location"]["lng"], phc_loc["lat"], phc_loc["lng"])
                available_ambs.append({"id": a["id"], "etaMin": rt["duration_min"]})
        
        available_ambs.sort(key=lambda x: x["etaMin"])
        ref["dispatch_queue"] = [a["id"] for a in available_ambs]
        ref["current_ambulance_index"] = 0
        if available_ambs:
            ref["dispatch_expires_at"] = datetime.utcnow().timestamp() + 15
        else:
            ref["dispatch_expires_at"] = 0

    # Handle Reservation Release on Rejection
    if data.status == "REJECTED_BY_HOSPITAL" and ref.get("selectedHospitalId"):
        hosp = next((h for h in db_hospitals if h["id"] == ref["selectedHospitalId"]), None)
        if hosp:
            # Restore inventory
            reqs = ref.get("resources", {})
            for key, req_val in reqs.items():
                if req_val and key in hosp["inventory"]:
                    if type(req_val) == bool:
                        hosp["inventory"][key] += 1
                    elif type(req_val) == int:
                        hosp["inventory"][key] += req_val

    ref["updatedAt"] = datetime.utcnow().isoformat()
    return {"success": True, "data": ref}

@app.post("/api/v1/matching")
def get_matching_hospitals(requirements: Dict[str, Any]):
    # Use PHC location
    phc_loc = db_phcs["phc-1"]["location"]
    
    matched = []
    rejected = []
    
    for h in db_hospitals:
        # Check resources
        reject_reasons = []
        if not h["accepting"]:
            reject_reasons.append("Hospital not accepting emergencies")
            
        # Needs ICU
        if requirements.get("icu") and h["inventory"].get("icu", 0) <= 0:
            reject_reasons.append("ICU unavailable")
            
        # Needs Ventilator
        if requirements.get("ventilator") and h["inventory"].get("ventilator", 0) <= 0:
            reject_reasons.append("Ventilator unavailable")
            
        # Needs Blood
        if requirements.get("blood") and h["inventory"].get("blood", 0) < requirements.get("bloodUnits", 1):
            reject_reasons.append(f"Insufficient blood units ({requirements.get('bloodGroup', 'Any')})")
            
        if reject_reasons:
            rejected.append({"hospital": h["name"], "reasons": reject_reasons})
            continue
            
        # Eligible - Calculate Route via OSRM
        route_info = get_osrm_route(phc_loc["lat"], phc_loc["lng"], h["location"]["lat"], h["location"]["lng"])
        
        h_copy = h.copy()
        h_copy["distanceKm"] = route_info["distance_km"]
        h_copy["etaMin"] = route_info["duration_min"]
        h_copy["reasons"] = [] # valid match
        matched.append(h_copy)
    
    # Sort by ETA
    matched.sort(key=lambda x: x["etaMin"])
    
    return {"success": True, "data": matched, "rejected": rejected}

@app.post("/api/v1/reservations")
def lock_resources(data: dict):
    hosp = next((h for h in db_hospitals if h["id"] == data.get("hospitalId")), None)
    if not hosp:
        return {"success": False, "message": "Hospital not found"}
        
    reqs = data.get("resources", {})
    
    # Validate before locking
    for key, req_val in reqs.items():
        if req_val and key in hosp["inventory"]:
            qty_needed = 1 if type(req_val) == bool else req_val
            if hosp["inventory"][key] < qty_needed:
                return {"success": False, "message": f"Conflict: {key} no longer available"}
                
    # Lock them
    for key, req_val in reqs.items():
        if req_val and key in hosp["inventory"]:
            qty_needed = 1 if type(req_val) == bool else req_val
            hosp["inventory"][key] -= qty_needed
            
    return {"success": True, "message": "Resources locked", "expiresIn": "04:32"}

@app.get("/api/v1/hospitals")
def get_hospitals():
    return {"success": True, "data": db_hospitals}

@app.get("/api/v1/hospitals/{hospital_id}/inventory")
def get_hospital_inventory(hospital_id: str):
    h = next((h for h in db_hospitals if h["id"] == hospital_id), None)
    if not h:
        return {"success": False, "message": "Not found"}
    return {"success": True, "data": h["inventory"]}

@app.put("/api/v1/hospitals/{hospital_id}/inventory")
def update_hospital_inventory(hospital_id: str, data: HospitalInventoryUpdate):
    h = next((h for h in db_hospitals if h["id"] == hospital_id), None)
    if not h:
        return {"success": False, "message": "Not found"}
    h["inventory"] = data.inventory
    return {"success": True, "data": h["inventory"]}

@app.get("/api/v1/ambulances")
def get_ambulances():
    # Update ETA to PHC for demo
    phc_loc = db_phcs["phc-1"]["location"]
    for a in db_ambulances:
        if a["status"] == "AVAILABLE":
            rt = get_osrm_route(a["location"]["lat"], a["location"]["lng"], phc_loc["lat"], phc_loc["lng"])
            a["distanceKm"] = rt["distance_km"]
            a["etaMin"] = rt["duration_min"]
            
    return {"success": True, "data": db_ambulances}

@app.put("/api/v1/ambulances/{ambulance_id}/status")
def update_ambulance_status(ambulance_id: str, data: AmbulanceStatusUpdate):
    a = next((a for a in db_ambulances if a["id"] == ambulance_id), None)
    if not a:
        return {"success": False}
    a["status"] = data.status
    return {"success": True, "data": a}

@app.get("/api/v1/ambulances/{ambulance_id}/alert")
def check_ambulance_alert(ambulance_id: str):
    now = datetime.utcnow().timestamp()
    for ref in db_referrals:
        if ref["status"] == "ACCEPTED" and ref.get("dispatch_queue"):
            # Check if timeout expired
            if now > ref.get("dispatch_expires_at", 0):
                ref["current_ambulance_index"] = ref.get("current_ambulance_index", 0) + 1
                ref["dispatch_expires_at"] = now + 15
            
            idx = ref["current_ambulance_index"]
            if idx < len(ref["dispatch_queue"]):
                if ref["dispatch_queue"][idx] == ambulance_id:
                    return {"success": True, "data": ref}
            else:
                # No more ambulances available
                pass
                
    return {"success": False, "message": "No active alert"}

@app.post("/api/v1/referrals/{referral_id}/accept_dispatch")
def accept_dispatch(referral_id: str, payload: dict):
    ref = next((r for r in db_referrals if r["id"] == referral_id), None)
    if not ref:
        return {"success": False, "message": "Not found"}
        
    ambulance_id = payload.get("ambulanceId")
    ref["status"] = "AMBULANCE_DISPATCHED"
    ref["ambulanceId"] = ambulance_id
    
    # Set ambulance to busy
    a = next((x for x in db_ambulances if x["id"] == ambulance_id), None)
    if a:
        a["status"] = "BUSY"
        
    return {"success": True, "data": ref}

@app.post("/api/v1/referrals/{referral_id}/decline_dispatch")
def decline_dispatch(referral_id: str, payload: dict):
    ref = next((r for r in db_referrals if r["id"] == referral_id), None)
    if not ref:
        return {"success": False, "message": "Not found"}
        
    # Advance queue immediately
    ref["current_ambulance_index"] = ref.get("current_ambulance_index", 0) + 1
    ref["dispatch_expires_at"] = datetime.utcnow().timestamp() + 15
    return {"success": True}

# --- MAP / SYSTEM DATA ---
@app.get("/api/v1/network")
def get_network_data():
    return {
        "success": True, 
        "data": {
            "hospitals": db_hospitals,
            "phcs": list(db_phcs.values()),
            "ambulances": db_ambulances
        }
    }

# Serve the static frontend files
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "pulsenet-gis-frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
