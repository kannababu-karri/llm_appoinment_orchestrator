from fastapi import FastAPI
from pydantic import BaseModel
from datetime import date
import requests
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

app = FastAPI(title="Agent Orchestrator")

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

#MCP Server
MCP_SERVER_9000 = "http://localhost:9000"  # Specializations

# Match the full Angular conversationState
class ChatRequest(BaseModel):
    message: Optional[str] = None
    patientId: str
    step: int
    selectedDate: Optional[str] = None
    specializationId: Optional[int] = None
    doctorId: Optional[str] = None
    slotId: Optional[int] = None
    slotStartTime: Optional[str] = None
    slotEndTime: Optional[str] = None

@app.post("/chat")
def chat(req: ChatRequest):
    print("req.step:", req.step)
    print("req.message:", req.message)
    print("req.selectedDate:", req.selectedDate)
    print("Conversation State:", req.dict())

    # STEP 1: Ask date
    if req.step == 1:
        return {"reply": "Please enter appointment date (YYYY-MM-DD)", "step": 2}

    # STEP 2: Validate date
    if req.step == 2:
        selected_date = req.selectedDate or req.message
        if not selected_date:
            return {"reply": "Date required", "step": 2}

        try:
            parsed_date = date.fromisoformat(selected_date)
        except:
            return {"reply": "Invalid date format (YYYY-MM-DD)", "step": 2}

        if parsed_date < date.today():
            return {"reply": "Date must be today or future", "step": 2}

        # Get specializations from mock API
        specs = requests.get(f"{MCP_SERVER_9000}/specializations").json()

        return {
            "reply": "Select specialization",
            "data": specs,
            "step": 3,
            "selectedDate": selected_date
        }

    # STEP 3: Get Doctors
    if req.step == 3 and req.specializationId:
        doctors = requests.get(
            f"{MCP_SERVER_9000}/doctors/by-specialization/{req.specializationId}"
        ).json()

        return {
            "reply": "Select doctor",
            "doctors": doctors,
            "step": 4
        }

    # STEP 4: Get Slots
    if req.step == 4 and req.doctorId and req.selectedDate:
        slots = requests.get(
            f"{MCP_SERVER_9000}/slots?doctorId={req.doctorId}&date={req.selectedDate}"
        ).json()

        return {
            "reply": "Select slot",
            "slots": slots,
            "step": 5
        }

    # STEP 5: Confirm booking
    if req.step == 5 and req.slotId:
        booking_payload = {
            "message": req.message,
            "patientId": req.patientId,
            "step": req.step,
            "selectedDate": req.selectedDate,
            "specializationId": req.specializationId,
            "doctorId": req.doctorId,
            "slotId": req.slotId
        }

        # Here you could save booking to DB
        try:
            response = requests.post(
                f"{MCP_SERVER_9000}/appointments",  # your appointment service
                json=booking_payload
            )

            if response.status_code == 200:
                return {
                    "reply": f"✅ Appointment confirmed {req.selectedDate} at {req.slotStartTime} - {req.slotEndTime}",
                    "step": 6
                }
            else:
                return {
                    "reply": "❌ Failed to book appointment. Try again.",
                    "step": 5
                }

        except Exception as e:
            return {
                "reply": f"❌ Error booking appointment: {str(e)}",
                "step": 5
            }

    return {"reply": "Invalid step", "step": req.step}