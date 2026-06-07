from __future__ import annotations

import os
import time
from pathlib import Path
from datetime import datetime, timezone

from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .agents import get_orchestration_status, run_all_agents
from .experience import (
    authenticate_user,
    get_marketplace_offers,
    register_user,
    run_what_if_simulation,
)
from . import storage
from .fixtures import load_personas
from .ml_model import ModelTrainingError, model_is_trained, predict_risk, train_model
from .routes.parse import router as parse_router
from .routes.score import router as score_router
from .resolver import resolve_scores
from .schemas import (
    AuthResponse,
    BorrowerProfileInput,
    BorrowerSignalInput,
    LoginRequest,
    MarketplaceResponse,
    RegisterRequest,
    RiskPredictionResponse,
    ScoreResponse,
    SignalType,
    StatementDerivationResponse,
    TrainModelResponse,
    WhatIfRequest,
    WhatIfResponse,
)
from .statement_parser import derive_signals_from_statement


def _seconds_until_expiry(expires_at_utc: str) -> int:
    expires_at = datetime.fromisoformat(expires_at_utc)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    remaining = int((expires_at - datetime.now(timezone.utc)).total_seconds())
    return max(1, remaining)

app = FastAPI(
    title="Cred-ible Scoring API",
    version="0.1.0",
    description="Dynamic alternative credit scoring API for credit-invisible borrowers.",
)

@app.on_event("startup")
async def startup_event():
    storage.init_db()
    print("Database initialized")

DEFAULT_ALLOWED_ORIGINS = [
    "https://cred-ible.vercel.app",
    "https://www.cred-ible.vercel.app",
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
]


def _allowed_origins() -> list[str]:
    configured = os.getenv("CREDIBLE_ALLOWED_ORIGINS", "")
    if configured.strip():
        return [origin.strip().rstrip("/") for origin in configured.split(",") if origin.strip()]

    return DEFAULT_ALLOWED_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_origin_regex=r"https://cred-ible(?:-[a-z0-9-]+)?\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(parse_router)
app.include_router(score_router)

DEMO_PERSONAS = load_personas()


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": "Cred-ible Scoring API",
        "status": "ok",
        "health": "/health",
        "docs": "/docs",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/orchestration/status")
async def orchestration_status() -> dict[str, str | int | bool | list[str]]:
    return get_orchestration_status()


@app.get("/personas")
async def list_personas() -> dict[str, list[dict[str, str]]]:
    return {
        "personas": [
            {"id": "raju", "name": "Raju", "profile": "Vegetable vendor"},
            {"id": "priya", "name": "Priya", "profile": "Freelance designer"},
            {"id": "mohammed", "name": "Mohammed", "profile": "Small shop owner"},
        ]
    }


@app.post("/score", response_model=ScoreResponse)
async def score_borrower(payload: BorrowerSignalInput) -> ScoreResponse:
    started = time.perf_counter()
    agent_outputs = await run_all_agents(payload)
    processing_time_ms = int((time.perf_counter() - started) * 1000)

    return resolve_scores(
        payload=payload,
        income=agent_outputs["income"],
        repayment=agent_outputs["repayment"],
        lifestyle=agent_outputs["lifestyle"],
        compliance=agent_outputs["compliance"],
        processing_time_ms=processing_time_ms,
    )


@app.post("/score/demo/{persona_id}", response_model=ScoreResponse)
async def score_demo_persona(persona_id: str) -> ScoreResponse:
    persona = DEMO_PERSONAS.get(persona_id.lower())
    if not persona:
        raise HTTPException(status_code=404, detail=f"Unknown demo persona '{persona_id}'")
    return await score_borrower(persona)


@app.post("/auth/login", response_model=AuthResponse)
async def login(payload: LoginRequest) -> AuthResponse:
    try:
        return authenticate_user(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/auth/register", response_model=AuthResponse)
async def register(payload: RegisterRequest) -> AuthResponse:
    try:
        return register_user(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/auth/me", response_model=AuthResponse)
async def who_am_i(authorization: str | None = Header(default=None)) -> AuthResponse:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="Expected 'Authorization: Bearer <token>'")

    s = storage.get_session(token.strip())
    if not s:
        raise HTTPException(status_code=401, detail="Invalid session")

    user = storage.get_user_by_id(s["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    organizations = user.get("organizations") or []
    primary_org = organizations[0] if organizations else {"name": "", "role": "analyst"}

    return AuthResponse(
        user_id=user["user_id"],
        full_name=user.get("full_name", ""),
        work_email=user.get("work_email", ""),
        organization=primary_org.get("name", ""),
        role=primary_org.get("role", "analyst"),
        session_token=s["session_token"],
        expires_in_seconds=_seconds_until_expiry(s["expires_at_utc"]),
        message="Session active",
    )


@app.post("/auth/logout")
async def logout(authorization: str | None = Header(default=None)) -> dict:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="Expected 'Authorization: Bearer <token>'")

    storage.delete_session(token.strip())
    return {"message": "Logged out"}


@app.post("/auth/password-reset/request")
async def password_reset_request(work_email: str) -> dict:
    if not work_email:
        raise HTTPException(status_code=400, detail="Missing work_email")
    token = storage.create_password_reset(work_email)
    # In real app we'd email the token. For demo return it.
    return {"message": "Password reset token created", "token": token}


@app.post("/auth/password-reset/confirm")
async def password_reset_confirm(token: str, new_password: str) -> dict:
    if not token or not new_password:
        raise HTTPException(status_code=400, detail="Missing token or password")
    ok = storage.consume_password_reset(token, new_password)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid token")
    return {"message": "Password updated"}


@app.post("/simulate/what-if", response_model=WhatIfResponse)
async def what_if(payload: WhatIfRequest) -> WhatIfResponse:
    return run_what_if_simulation(payload)


@app.post("/signals/derive", response_model=StatementDerivationResponse)
async def derive_statement_signals(
    signal_type: SignalType,
    statement: UploadFile = File(...),
) -> StatementDerivationResponse:
    try:
        content = await statement.read()
        if not content:
            raise ValueError("Uploaded statement is empty.")
        derivation = derive_signals_from_statement(
            signal_type=signal_type,
            filename=statement.filename or "",
            content=content,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return StatementDerivationResponse(
        signal_type=signal_type,
        derived_fields=derivation.derived_fields,
        summary=derivation.summary,
        rows_processed=derivation.rows_processed,
    )


@app.get("/marketplace/offers", response_model=MarketplaceResponse)
async def marketplace_offers(score: int = 670) -> MarketplaceResponse:
    return get_marketplace_offers(score, None)


@app.get("/model/status")
async def model_status() -> dict[str, bool]:
    return {"trained": model_is_trained()}


@app.post("/model/train", response_model=TrainModelResponse)
async def train_credit_model(dataset_file: str | None = None) -> TrainModelResponse:
    try:
        dataset_path = Path(dataset_file) if dataset_file else None
        result = train_model(dataset_path=dataset_path)
    except ModelTrainingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TrainModelResponse(**result.__dict__)


@app.post("/model/predict-risk", response_model=RiskPredictionResponse)
async def predict_credit_risk(payload: BorrowerProfileInput) -> RiskPredictionResponse:
    try:
        predicted_risk, class_probabilities, model_trained_at = predict_risk(payload.model_dump())
    except ModelTrainingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if predicted_risk not in {"low", "medium", "high"}:
        raise HTTPException(status_code=500, detail=f"Unexpected model class '{predicted_risk}'.")

    return RiskPredictionResponse(
        predicted_risk=predicted_risk,
        class_probabilities=class_probabilities,
        model_trained_at_utc=model_trained_at,
    )
