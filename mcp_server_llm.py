from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI(title="MCP LLM Orchestrator")

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
AI_AGENT_SERVICE = "http://localhost:8094" 

@app.get("/specializations")
def get_specializations(request: Request):
    auth_header = request.headers.get('Authorization')
    headers = {'Authorization': auth_header} if auth_header else {}
    try:
        response = requests.get(f"{AI_AGENT_SERVICE}/api/specializations", headers=headers)
        print("response.json() specializations", response.json())
        return response.json()
    except Exception as e:
        return {"error": f"Failed to fetch specializations: {str(e)}"}

@app.get("/doctors/by-specialization/{spec_id}")
def get_doctors(spec_id: int, request: Request):
    auth_header = request.headers.get('Authorization')
    headers = {'Authorization': auth_header} if auth_header else {}
    try:
        response = requests.get(f"{AI_AGENT_SERVICE}/api/doctors/by-specialization/{spec_id}", headers=headers)
        print("response.json() doctors", response.json())
        return response.json()
    except Exception as e:
        return {"error": f"Failed to fetch doctors: {str(e)}"}

@app.get("/slots")
def get_slots(doctorId: str, date: str, request: Request):
    auth_header = request.headers.get('Authorization')
    headers = {'Authorization': auth_header} if auth_header else {}
    try:
        response = requests.get(f"{AI_AGENT_SERVICE}/api/slots?doctorId={doctorId}&date={date}", headers=headers)
        print("response.json() slots", response.json())
        return response.json()
    except Exception as e:
        return {"error": f"Failed to fetch slots: {str(e)}"}

@app.post("/appointments")
async def book_appointment(request: Request):
    payload = await request.json()
    auth_header = request.headers.get('Authorization')
    headers = {'Authorization': auth_header} if auth_header else {}
    try:
        response = requests.post(f"{AI_AGENT_SERVICE}/api/appointments", json=payload, headers=headers)
        print("response.json() appointments", response.json())
        return response.json()
    except Exception as e:
        return {"error": f"Failed to book appointment: {str(e)}"}