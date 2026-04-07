# file: llm_orchestrator.py
from fastapi import FastAPI, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import requests
import openai
import json
from fastapi.responses import HTMLResponse
import os
import logging
from dotenv import load_dotenv

log_dir = "/opt/apps/patient-appointment/logs"
os.makedirs(log_dir, exist_ok=True)

load_dotenv()  # This loads variables from .env

logging.basicConfig(
    filename=os.path.join(log_dir, "appointment-agent-llm.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logging.info("Appointment LLM Agent Orchestrator API service started.")

# -------------------------------
# LLM Configuration
# -------------------------------
openai.api_key = os.getenv("OPENAI_API_KEY")  # Set this in your environment
if openai.api_key is None:
    raise {"reply": "OPENAI_API_KEY is not set in your .env file"}

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

        logging.info(f"LLM output_text: {output_text}")

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
MCP_BASE = "http://localhost:8004"
SPECIALIZATION_SERVICE = f"{MCP_BASE}/specializations"
DOCTOR_SERVICE = f"{MCP_BASE}/doctors"
SLOT_SERVICE = f"{MCP_BASE}/slots"
APPOINTMENT_SERVICE = f"{MCP_BASE}/appointments"


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

@app.get("/test-appointment_agent_llm", response_class=HTMLResponse)
def home():
    return """
    <html>
    <body>
        <h2>Title: Appointment LLM Agent Orchestrator</h2>
        <h2>Appointment LLM Agent Orchestrator API Service response is good.</h2>
    </body>
    </html>
    """

# -------------------------------
# Chat Endpoint
# -------------------------------
@app.post("/api/llmChatAppointment")
def chat(req: ChatRequest, request: Request):
    auth_header = request.headers.get('Authorization')
    headers = {'Authorization': auth_header} if auth_header else {}
    state = req.dict()
    print("ChatRequest state", state)
    logging.info(f"ChatRequest: {state}")

    # STEP 1: Ask for date
    if req.step == 1:
        return {"reply": "Hello! Please enter appointment date (YYYY-MM-DD)", "step": 2}

    # STEP 2: Validate date and normalize with LLM
    if req.step == 2:
        if not req.message:
            return {"reply": "⚠️ Date required", "step": 2}
        state['selectedDate'] = req.message
        # Skip LLM for reply, use database specializations directly
        # Fetch specializations from MCP
        try:
            specs = requests.get(SPECIALIZATION_SERVICE, headers=headers).json()
            logging.info(f"specs: {specs}")
        except:
            specs = []
        return {
            "reply": "Please select a specialization:",
            "step": 3,  # Advance to next step
            "data": specs
        }

    # STEP 3: Map specialization to doctors
    if req.step == 3 and req.specializationId:
        try:
            doctors = requests.get(f"{DOCTOR_SERVICE}/by-specialization/{req.specializationId}", headers=headers).json()
            logging.info(f"doctors: {doctors}")
        except:
            doctors = []
        # Skip LLM for reply, use database doctors directly
        reply = "Please select a doctor from the available options:"
        return {
            "reply": reply,
            "step": 4,  # Advance to next step
            "doctors": doctors
        }

    # STEP 4: Map doctor to available slots
    if req.step == 4 and req.doctorId and req.selectedDate:
        try:
            slots = requests.get(f"{SLOT_SERVICE}?doctorId={req.doctorId}&date={req.selectedDate}", headers=headers).json()
        except:
            slots = []
        # Skip LLM for reply, use database slots directly
        return {
            "reply": "Please select an available slot:",
            "step": 5,  # Advance to next step
            "slots": slots
        }

    # STEP 5: Confirm appointment
    if req.step == 5 and req.slotId:
        #booking_payload = state
        try:
            booking_payload = {
                "message": req.message,
                "patientId": req.patientId,
                "step": req.step,
                "selectedDate": req.selectedDate,
                "specializationId": req.specializationId,
                "doctorId": req.doctorId,
                "slotId": req.slotId
            }
            resp = requests.post(APPOINTMENT_SERVICE, json=booking_payload, headers=headers)
            logging.info(f"resp req.step == 5: {resp}")
            confirmation = llm_process_step("confirm appointment", state)
            if resp.status_code == 200:
                confirmation['reply'] = f"✅ Appointment confirmed {req.selectedDate} at {req.slotStartTime} - {req.slotEndTime}"
                confirmation['step'] = 6
            else:
                confirmation['reply'] = "❌ Failed to book appointment"
                confirmation['step'] = 5
        except Exception as e:
            confirmation = {"reply": f"❌ Error booking appointment: {str(e)}", "step": 5}
        logging.info(f"confirmation req.step == 5: {confirmation}")
        return confirmation

    return {"reply": "Invalid step", "step": req.step}