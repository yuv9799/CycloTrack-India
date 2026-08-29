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

import os
from typing import List, Optional

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

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
