from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI(title="MCP Orchestrator")

# Allow Angular dev server
origins = [
    "http://localhost:4200",
    "http://127.0.0.1:4200"
]

# Enable CORS for Angular frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base URLs of microservices
SPECIALIZATION_SERVICE = "http://localhost:8094"  # Specializations
DOCTOR_SERVICE = "http://localhost:8094"          # Doctors
SLOT_SERVICE = "http://localhost:8094"            # Slots
APPOINTMENT_SERVICE = "http://localhost:8094"     # Appointments

@app.get("/specializations")
def get_specializations():
    try:
        response = requests.get(f"{SPECIALIZATION_SERVICE}/api/specializations")
        return response.json()
    except Exception as e:
        return {"error": f"Failed to fetch specializations: {str(e)}"}

@app.get("/doctors/by-specialization/{spec_id}")
def get_doctors(spec_id: int):
    try:
        response = requests.get(f"{DOCTOR_SERVICE}/api/doctors/by-specialization/{spec_id}")
        return response.json()
    except Exception as e:
        return {"error": f"Failed to fetch doctors: {str(e)}"}

@app.get("/slots")
def get_slots(doctorId: str, date: str):
    try:
        response = requests.get(f"{SLOT_SERVICE}/api/slots?doctorId={doctorId}&date={date}")
        return response.json()
    except Exception as e:
        return {"error": f"Failed to fetch slots: {str(e)}"}

@app.post("/appointments")
async def book_appointment(request: Request):
    payload = await request.json()
    try:
        response = requests.post(f"{APPOINTMENT_SERVICE}/api/appointments", json=payload)
        return response.json()
    except Exception as e:
        return {"error": f"Failed to book appointment: {str(e)}"}