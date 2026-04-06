# file: llm_orchestrator.py
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from datetime import date
import requests
import os
import openai
import json

# -------------------------------
# LLM Configuration
# -------------------------------
openai.api_key = os.getenv("OPENAI_API_KEY")  # Set this in your environment

def llm_process_step(user_message: str, state: dict) -> dict:
    """
    Uses LLM to decide the next step, normalize input, generate replies.
    """
    prompt = f"""
You are a hospital appointment assistant. Current step: {state['step']}.
User input: {user_message}
Conversation state: {json.dumps(state)}
Return JSON:
{{ "reply": "...", "step": next_step_number }}
"""
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        output_text = response.choices[0].message.content.strip()
        return json.loads(output_text)
    except Exception as e:
        return {"reply": f"❌ LLM error: {str(e)}", "step": state.get("step", 1)}


# -------------------------------
# FastAPI Setup
# -------------------------------
app = FastAPI(title="Agent LLM Orchestrator")

origins = ["http://localhost:4200", "http://127.0.0.1:4200"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MCP Microservices
MCP_BASE = "http://localhost:9001"
SPECIALIZATION_SERVICE = f"{MCP_BASE}/api/specializations"
DOCTOR_SERVICE = f"{MCP_BASE}/api/doctors"
SLOT_SERVICE = f"{MCP_BASE}/api/slots"
APPOINTMENT_SERVICE = f"{MCP_BASE}/api/appointments"


# -------------------------------
# Pydantic Chat Model
# -------------------------------
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

# -------------------------------
# Chat Endpoint
# -------------------------------
@app.post("/chat")
def chat(req: ChatRequest):
    state = req.dict()

    # STEP 1: Ask for date
    if req.step == 1:
        return {"reply": "Hello! Please enter appointment date (YYYY-MM-DD)", "step": 2}

    # STEP 2: Validate date and normalize with LLM
    if req.step == 2:
        if not req.message:
            return {"reply": "⚠️ Date required", "step": 2}
        state['selectedDate'] = req.message
        llm_output = llm_process_step(req.message, state)

        # Fetch specializations from MCP
        try:
            specs = requests.get(SPECIALIZATION_SERVICE).json()
        except:
            specs = []
        llm_output['data'] = specs
        return llm_output

    # STEP 3: Map specialization to doctors
    if req.step == 3 and req.specializationId:
        try:
            doctors = requests.get(f"{DOCTOR_SERVICE}/by-specialization/{req.specializationId}").json()
        except:
            doctors = []
        llm_output = llm_process_step(req.message or "", state)
        llm_output['doctors'] = doctors
        return llm_output

    # STEP 4: Map doctor to available slots
    if req.step == 4 and req.doctorId and req.selectedDate:
        try:
            slots = requests.get(f"{SLOT_SERVICE}?doctorId={req.doctorId}&date={req.selectedDate}").json()
        except:
            slots = []
        llm_output = llm_process_step(req.message or "", state)
        llm_output['slots'] = slots
        return llm_output

    # STEP 5: Confirm appointment
    if req.step == 5 and req.slotId:
        booking_payload = state
        try:
            resp = requests.post(APPOINTMENT_SERVICE, json=booking_payload)
            confirmation = llm_process_step("confirm appointment", state)
            if resp.status_code == 200:
                confirmation['reply'] = f"✅ Appointment confirmed {req.selectedDate} at {req.slotStartTime} - {req.slotEndTime}"
                confirmation['step'] = 6
            else:
                confirmation['reply'] = "❌ Failed to book appointment"
                confirmation['step'] = 5
        except Exception as e:
            confirmation = {"reply": f"❌ Error booking appointment: {str(e)}", "step": 5}
        return confirmation

    return {"reply": "Invalid step", "step": req.step}