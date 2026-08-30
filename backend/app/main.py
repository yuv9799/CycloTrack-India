"""
CycloneAI backend — FastAPI entrypoint.

Currently exposes a single feature: a real, open-domain AI chat endpoint
(`/api/chat`) that powers the "CycloBot" widget on the frontend. It's a
thin wrapper around OpenRouter (https://openrouter.ai) using its free
(":free") model tier, so unlike the old keyword matcher it can actually
understand and answer *any* phrasing of a cyclone-related question (and
reasonable follow-ups), not just the exact intents someone hard-coded —
at no API cost.

Run locally:
    cd backend
    python -m venv venv && source venv/bin/activate      # or venv\\Scripts\\activate on Windows
    pip install -r requirements.txt
    cp .env.example .env                                  # then fill in OPENROUTER_API_KEY
    uvicorn app.main:app --reload --port 8000

Get a free key (no credit card required) at https://openrouter.ai/keys.

The frontend widget (frontend/assets/chatbot.js) talks to this server at
POST /api/chat. If the server is unreachable or OPENROUTER_API_KEY isn't
set, the widget automatically falls back to its old offline knowledge
base so the demo still works without a backend running.
"""

import json
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

load_dotenv()

APP_TITLE = "CycloneAI Backend"
API_KEY = os.getenv("OPENROUTER_API_KEY")
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")]
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Free-tier model IDs on OpenRouter rotate as providers add/remove them, so we
# try a short ordered list and fall back to OpenRouter's own free auto-router
# (which picks *some* working free model for you) if all of the pinned ones
# are rate-limited or delisted. Override the primary via .env if you have a
# favorite. See https://openrouter.ai/models?max_price=0 for the live list.
PRIMARY_MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
FALLBACK_MODELS = [
    m.strip()
    for m in os.getenv(
        "OPENROUTER_FALLBACK_MODELS",
        "openai/gpt-oss-20b:free,openrouter/free",
    ).split(",")
    if m.strip()
]

app = FastAPI(title=APP_TITLE)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SYSTEM_PROMPT = """You are CycloBot, the AI assistant embedded in CycloneAI, a Smart India \
Hackathon 2026 project (Problem SIH26070, Ministry of Earth Sciences) that detects, \
classifies, and predicts tropical cyclone patterns from multi-source satellite data.

You can hold a real, open-ended conversation — don't just match canned phrases. Answer \
whatever the user actually asks, using follow-up context from earlier turns.

Your primary focus is tropical cyclones / hurricanes / typhoons: how and why they form, \
their structure, categories (IMD scale for the North Indian Ocean and Saffir-Simpson for \
Atlantic/Pacific storms), naming conventions, historical storms (in India and globally), \
forecasting and tracking methods, storm surge and other impacts, climate-change links, \
and safety/preparedness guidance (IMD/NDMA color-coded alerts, evacuation basics, etc.). \
You can also explain how this CycloneAI project itself works (detection, classification, \
intensity and trajectory prediction, explainability) at a conceptual level.

You may draw on general science, geography, or disaster-management knowledge to answer \
reasonable follow-ups, but steer the conversation back toward cyclones if it wanders far \
off topic — you're a cyclone specialist, not a general-purpose assistant.

Important honesty rules:
- You do not have live/real-time data feeds. If asked about a currently active storm, say \
so plainly and point the user to IMD (mausam.imd.gov.in) or NDMA for official, up-to-date \
bulletins, rather than guessing.
- You are an educational assistant, not an emergency service. For any real safety decision, \
tell the user to follow official IMD/NDMA warnings and local authority instructions over \
anything you say.
- If you don't know something, say so rather than inventing details (e.g. don't fabricate \
specific numbers, dates, or death tolls you're not confident about).

Style: keep replies conversational and concise for a chat widget — short paragraphs and/or \
brief bullet lists. Expand only if the user asks for more depth. You may use light HTML \
formatting (<strong>, <em>, <ul><li>) since the widget renders it, but keep it minimal.
"""

MAX_HISTORY_TURNS = 12
MAX_MESSAGE_LEN = 2000


class ChatMessage(BaseModel):
    role: str
    content: str = Field(..., max_length=MAX_MESSAGE_LEN)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=MAX_MESSAGE_LEN)
    history: List[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str


# ---------------------------------------------------------------------------
# Emergency / help-request handling (POST /api/help-requests)
#
# The static frontend is served from GitHub Pages without a live backend, so
# the "Report / Request Help" form on the frontend tries this endpoint first
# and, if it is unreachable, falls back to storing the request in the browser
# (localStorage) to avoid losing a person's emergency data.
#
# Submissions are persisted as JSON lines in a data file. No personal
# information is ever exposed back through a public GET route.
# ---------------------------------------------------------------------------
INDIA_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Andaman & Nicobar Islands", "Chandigarh", "Delhi (NCT)", "Jammu & Kashmir",
    "Ladakh", "Lakshadweep", "Puducherry", "Other",
]
EMERGENCY_TYPES = [
    "Medical Emergency", "Food Required", "Drinking Water Required",
    "Shelter Required", "Rescue Required", "Missing Person", "Transportation Required", "Other",
]
HELP_REQUESTS_FILE = Path(os.getenv("HELP_REQUESTS_FILE", "data/help_requests.jsonl"))
_help_lock = threading.Lock()
_MOBILE_RE = re.compile(r"^\+?[0-9\s\-()]{6,15}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MAX_IMAGE_CHARS = 3_000_000  # ~2MB of base64-encoded image data


def _clean_digits(value: str) -> str:
    return re.sub(r"[^0-9]", "", value)


class HelpRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=120)
    mobile: str = Field(..., min_length=6, max_length=20)
    email: Optional[str] = Field(default=None, max_length=120)
    state: str = Field(..., min_length=2, max_length=80)
    district: str = Field(..., min_length=2, max_length=120)
    village_city: str = Field(..., min_length=2, max_length=140)
    current_location: str = Field(..., min_length=2, max_length=400)
    people_affected: int = Field(..., ge=1, le=1_000_000)
    children: int = Field(default=0, ge=0, le=1_000_000)
    elderly_disabled: int = Field(default=0, ge=0, le=1_000_000)
    emergency_types: List[str] = Field(..., min_length=1, max_length=len(EMERGENCY_TYPES))
    description: str = Field(..., min_length=5, max_length=3000)
    image: Optional[str] = Field(default=None)
    consent: bool = True

    @field_validator("mobile")
    @classmethod
    def _validate_mobile(cls, v: str) -> str:
        if not _MOBILE_RE.match(v.strip()):
            raise ValueError("Enter a valid phone number (6–15 digits, optional + / spaces).")
        if not (8 <= len(_clean_digits(v)) <= 15):
            raise ValueError("Enter a valid phone number.")
        return v.strip()

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip() and not _EMAIL_RE.match(v.strip()):
            raise ValueError("Enter a valid email address (or leave it empty).")
        return v.strip() if v else None

    @field_validator("emergency_types")
    @classmethod
    def _validate_types(cls, v: List[str]) -> List[str]:
        cleaned = [t.strip() for t in v if t and t.strip()]
        unknown = [t for t in cleaned if t not in EMERGENCY_TYPES]
        if unknown:
            raise ValueError(f"Unknown emergency type(s): {', '.join(unknown)}")
        if not cleaned:
            raise ValueError("Select at least one emergency type.")
        return cleaned

    @field_validator("image")
    @classmethod
    def _validate_image(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not v.strip():
            return None
        if len(v) > _MAX_IMAGE_CHARS:
            raise ValueError("Image is too large (max ~2MB).")
        if not v.startswith("data:image/"):
            raise ValueError("Image must be a data URL (data:image/...).")
        return v


class HelpResponse(BaseModel):
    status: str
    id: str
    message: str


def _load_help_requests() -> List[dict]:
    if not HELP_REQUESTS_FILE.exists():
        return []
    records = []
    try:
        with HELP_REQUESTS_FILE.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        return []
    return records


def _save_help_request(record: dict) -> None:
    HELP_REQUESTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with _help_lock:
        # Append-only JSON-lines file: each line is one complete record.
        with HELP_REQUESTS_FILE.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


@app.post("/api/help-requests", response_model=HelpResponse)
def submit_help_request(req: HelpRequest):
    if not req.consent:
        raise HTTPException(status_code=400, detail="You must consent to submit an emergency request.")

    record_id = (
        f"HR-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{os.urandom(2).hex().upper()}"
    )
    record = {
        "id": record_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        **req.model_dump(exclude_none=True),
    }

    try:
        _save_help_request(record)
    except OSError as e:
        raise HTTPException(
            status_code=500,
            detail="Your request could not be saved right now. Please try again or call 112.",
        ) from e

    return HelpResponse(
        status="ok",
        id=record_id,
        message="Your emergency request has been received and logged.",
    )


@app.get("/api/help-requests")
def count_help_requests():
    """Public summary route — returns only aggregate counts, never personal data."""
    records = _load_help_requests()
    by_type: dict = {}
    for r in records:
        for t in r.get("emergency_types", []):
            by_type[t] = by_type.get(t, 0) + 1
    return {
        "total_received": len(records),
        "by_emergency_type": by_type,
    }



# ---------------------------------------------------------------------------
# Response Center APIs (prototype-safe, provider-ready)
# ---------------------------------------------------------------------------
from math import radians, sin, cos, asin, sqrt

RESPONSE_DATA_DIR = Path(os.getenv("RESPONSE_DATA_DIR", "data"))
MISSING_PERSONS_FILE = RESPONSE_DATA_DIR / "missing_persons.jsonl"

DEMO_SHELTERS = [
    {"id":"SH-001","name":"Puri Coastal Shelter","district":"Puri","state":"Odisha","lat":19.8135,"lng":85.8312,"capacity":500,"available":182,"water":True,"food":True,"medical":True,"accessible":True},
    {"id":"SH-002","name":"Gopalpur Cyclone Shelter","district":"Ganjam","state":"Odisha","lat":19.2676,"lng":84.9050,"capacity":420,"available":96,"water":True,"food":True,"medical":False,"accessible":True},
    {"id":"SH-003","name":"Kakinada Relief Shelter","district":"Kakinada","state":"Andhra Pradesh","lat":16.9891,"lng":82.2475,"capacity":600,"available":240,"water":True,"food":True,"medical":True,"accessible":False},
    {"id":"SH-004","name":"Srikakulam Safe Center","district":"Srikakulam","state":"Andhra Pradesh","lat":18.2969,"lng":83.8973,"capacity":350,"available":140,"water":True,"food":False,"medical":True,"accessible":True},
    {"id":"SH-005","name":"Paradip Community Shelter","district":"Jagatsinghpur","state":"Odisha","lat":20.3160,"lng":86.6080,"capacity":450,"available":210,"water":True,"food":True,"medical":True,"accessible":True},
    {"id":"SH-006","name":"Digha Emergency Shelter","district":"Purba Medinipur","state":"West Bengal","lat":21.6280,"lng":87.5080,"capacity":380,"available":72,"water":True,"food":True,"medical":False,"accessible":True},
]

class RiskRequest(BaseModel):
    location: str = Field(..., min_length=2, max_length=200)
    coast_distance_km: float = Field(..., ge=0, le=1000)
    wind_kmh: float = Field(..., ge=0, le=400)
    rainfall_mm: float = Field(..., ge=0, le=2000)
    storm_surge_m: float = Field(..., ge=0, le=20)
    vulnerability: str = Field(default="medium")

@app.get("/api/v1/shelters")
def get_shelters(q: Optional[str] = None):
    rows = DEMO_SHELTERS
    if q:
        needle = q.strip().lower()
        rows = [x for x in rows if needle in x["name"].lower() or needle in x["district"].lower() or needle in x["state"].lower()]
    return {"mode":"demo","data_source":"Demo shelter registry","shelters":rows}

@app.get("/api/v1/shelters/nearest")
def nearest_shelters(lat: float, lng: float, limit: int = 5):
    def hav(a,b,c,d):
        R=6371.0
        p1,p2=radians(a),radians(c)
        dp=radians(c-a); dl=radians(d-b)
        x=sin(dp/2)**2+cos(p1)*cos(p2)*sin(dl/2)**2
        return R*2*asin(sqrt(x))
    rows=[]
    for s in DEMO_SHELTERS:
        item=dict(s); item["distance_km"]=round(hav(lat,lng,s["lat"],s["lng"]),2); rows.append(item)
    return {"mode":"demo","data_source":"Demo shelter registry","shelters":sorted(rows,key=lambda x:x["distance_km"])[:max(1,min(limit,20))]}

@app.post("/api/v1/risk/assess")
def assess_risk(req: RiskRequest):
    v={"low":0,"medium":8,"high":15}.get(req.vulnerability.lower(),8)
    score=min(100,(req.wind_kmh/2)+(req.rainfall_mm/8)+(req.storm_surge_m*10)+max(0,30-req.coast_distance_km)+v)
    level="EXTREME" if score>=75 else "HIGH" if score>=55 else "MODERATE" if score>=30 else "LOW"
    return {"mode":"demo","score":round(score,1),"level":level,"location":req.location,"official_warning_note":"Prototype assessment only. Follow official IMD/NDMA/local authority warnings."}

class MissingPerson(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    age: int = Field(..., ge=0, le=120)
    gender: str = Field(default="", max_length=40)
    last_seen: str = Field(..., min_length=1, max_length=80)
    location: str = Field(..., min_length=2, max_length=300)
    details: str = Field(..., min_length=2, max_length=1500)
    contact_name: str = Field(..., min_length=1, max_length=120)
    contact_phone: str = Field(..., min_length=6, max_length=20)

@app.post("/api/v1/missing-persons")
def create_missing_person(req: MissingPerson):
    RESPONSE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    rid=f"MP-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{os.urandom(2).hex().upper()}"
    record={"id":rid,"created_at":datetime.now(timezone.utc).isoformat(),"status":"Missing",**req.model_dump()}
    with MISSING_PERSONS_FILE.open("a",encoding="utf-8") as fh:
        fh.write(json.dumps(record,ensure_ascii=False)+"\n")
    return {"status":"ok","id":rid,"message":"Missing-person report received. Access is restricted to authorised responders."}

@app.get("/api/v1/alerts")
def get_alerts():
    return {"mode":"demo","alerts":[
        {"id":"AL-001","severity":"HIGH","type":"Track change","title":"Cyclone track update","message":"Review the latest official forecast before making evacuation decisions.","created_at":datetime.now(timezone.utc).isoformat()},
        {"id":"AL-002","severity":"HIGH","type":"Storm surge","title":"Coastal surge risk","message":"Low-lying coastal areas should follow local evacuation instructions.","created_at":datetime.now(timezone.utc).isoformat()}
    ]}

@app.get("/api/v1/data-sources/status")
def data_source_status():
    return {"mode":"demo","sources":[
        {"name":"Satellite","status":"demo","provider":"SatelliteDataProvider"},
        {"name":"Weather","status":"demo","provider":"WeatherDataProvider"},
        {"name":"Cyclone feed","status":"demo","provider":"CycloneDataProvider"},
        {"name":"Ocean","status":"demo","provider":"OceanDataProvider"}
    ]}

@app.get("/api/v1/predictions/landfall/{cyclone_id}")
def landfall_prediction(cyclone_id: str):
    return {"mode":"demo","cyclone_id":cyclone_id,"region":"Odisha–Andhra coastal belt","time_window_hours":"18–24","wind_kmh":"130–145","confidence":0.78,"uncertainty_km":85}

@app.get("/api/v1/predictions/storm-surge/{cyclone_id}")
def storm_surge_prediction(cyclone_id: str):
    return {"mode":"demo","cyclone_id":cyclone_id,"risk":"HIGH","estimated_range_m":"2–3.5","note":"Prototype estimate; use validated scientific surge guidance for operational decisions."}

@app.get("/api/v1/predictions/flood/{cyclone_id}")
def flood_prediction(cyclone_id: str):
    return {"mode":"demo","cyclone_id":cyclone_id,"risk":"HIGH","rainfall_risk":"HIGH","waterlogging":"POSSIBLE","note":"Demo hazard layer; not an official flood warning."}


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "model": PRIMARY_MODEL,
        "ai_configured": bool(API_KEY),
    }


def _call_openrouter(model: str, messages: list) -> requests.Response:
    return requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            # Optional but recommended by OpenRouter for usage attribution;
            # harmless to send even for local dev.
            "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "https://cyclonai.local"),
            "X-Title": "CycloneAI CycloBot",
        },
        json={"model": model, "messages": messages, "max_tokens": 700},
        timeout=30,
    )


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not API_KEY:
        raise HTTPException(
            status_code=503,
            detail="OPENROUTER_API_KEY is not configured on the server. "
            "Get a free key at https://openrouter.ai/keys, set it in backend/.env, "
            "and restart the server.",
        )

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in req.history[-MAX_HISTORY_TURNS:]:
        if m.role in ("user", "assistant") and m.content.strip():
            messages.append({"role": m.role, "content": m.content})
    messages.append({"role": "user", "content": req.message})

    last_error = None
    for model in [PRIMARY_MODEL, *FALLBACK_MODELS]:
        try:
            resp = _call_openrouter(model, messages)
        except requests.RequestException as e:
            last_error = str(e)
            continue

        if resp.status_code == 429:
            # Free-tier rate limit hit on this model — try the next one.
            last_error = f"{model} rate-limited (429)"
            continue
        if not resp.ok:
            last_error = f"{model} returned {resp.status_code}: {resp.text[:200]}"
            continue

        try:
            data = resp.json()
            reply = data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, ValueError) as e:
            last_error = f"{model} returned an unparseable response: {e}"
            continue

        if reply:
            return ChatResponse(reply=reply)
        last_error = f"{model} returned an empty reply"

    raise HTTPException(
        status_code=502,
        detail=f"All OpenRouter free models failed. Last error: {last_error}",
    )
