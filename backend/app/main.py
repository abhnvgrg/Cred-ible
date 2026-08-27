from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .agents import get_orchestration_status, run_all_agents
from . import storage
from .auth import (
    AuthError,
    authenticate,
    get_current_user,
    check_login_allowed,
    clear_login_failures,
    create_session,
    create_user,
    end_session,
    get_current_user,
    init_db,
    record_login_failure,
    require_admin,
)
from .experience import get_marketplace_offers, run_what_if_simulation
from .fixtures import load_personas
from .ml_model import (
    ModelTrainingError,
    available_datasets,
    model_is_trained,
    predict_risk,
    resolve_dataset_key,
    train_model,
)
from .routes.parse import router as parse_router
from .routes.score import router as score_router
from .resolver import resolve_scores
from .schemas import (
    AuthResponse,
    BorrowerProfileInput,
    BorrowerSignalInput,
    LoginRequest,
    MarketplaceResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
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

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


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
    lifespan=lifespan,
)

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
async def score_borrower(
    payload: BorrowerSignalInput,
    _: dict = Depends(get_current_user),
) -> ScoreResponse:
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


def _auth_response(user: dict, message: str, token: str, ttl: int) -> AuthResponse:
    return AuthResponse(
        user_id=user["user_id"],
        full_name=user["full_name"],
        work_email=user["work_email"],
        organization=user["organization"],
        role=user["role"],
        session_token=token,
        expires_in_seconds=ttl,
        message=message,
    )


@app.post("/auth/login", response_model=AuthResponse)
async def login(payload: LoginRequest) -> AuthResponse:
    key = payload.email.strip().lower()
    check_login_allowed(key)

    user = authenticate(payload.email, payload.password)
    if user is None:
        record_login_failure(key)
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    clear_login_failures(key)
    token, ttl = create_session(user["user_id"])
    return _auth_response(user, "Signed in successfully.", token, ttl)


@app.post("/auth/register", response_model=AuthResponse, status_code=201)
async def register(payload: RegisterRequest) -> AuthResponse:
    if payload.password != payload.confirm_password:
        raise HTTPException(
            status_code=400, detail="Password and confirm password must match."
        )
    try:
        user = create_user(
            email=payload.work_email,
            password=payload.password,
            full_name=payload.full_name,
            organization=payload.organization,
        )
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    token, ttl = create_session(user["user_id"])
    return _auth_response(user, "Workspace account created successfully.", token, ttl)


@app.get("/auth/me", response_model=AuthResponse)
async def who_am_i(user: dict = Depends(get_current_user)) -> AuthResponse:
    return _auth_response(
        user,
        "Session active.",
        user["session_token"],
        _seconds_until_expiry(user["expires_at_utc"]),
    )


@app.post("/auth/logout")
async def logout(user: dict = Depends(get_current_user)) -> dict:
    end_session(user["session_token"])
    return {"message": "Signed out."}


@app.post("/auth/password-reset/request")
async def password_reset_request(payload: PasswordResetRequest) -> dict:
    try:
        token = storage.create_password_reset(payload.work_email)
    except AuthError:
        token = None

    if token is not None and os.getenv("CREDIBLE_ENV", "development").lower() not in {
        "prod",
        "production",
    }:
        logger.info("Password reset token for %s: %s", payload.work_email, token)

    return {
        "message": (
            "If an account exists for that address, a reset link has been sent."
        )
    }


@app.post("/auth/password-reset/confirm")
async def password_reset_confirm(payload: PasswordResetConfirm) -> dict:
    try:
        ok = storage.consume_password_reset(payload.token, payload.new_password)
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not ok:
        raise HTTPException(
            status_code=400, detail="That reset link is invalid or has expired."
        )
    return {"message": "Password updated. Please sign in again."}


@app.post("/simulate/what-if", response_model=WhatIfResponse)
async def what_if(
    payload: WhatIfRequest,
    _: dict = Depends(get_current_user),
) -> WhatIfResponse:
    return run_what_if_simulation(payload)


@app.post("/signals/derive", response_model=StatementDerivationResponse)
async def derive_statement_signals(
    signal_type: SignalType,
    statement: UploadFile = File(...),
    _: dict = Depends(get_current_user),
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


@app.get("/model/datasets")
async def list_trainable_datasets(_: dict = Depends(require_admin)) -> dict:
    return {"datasets": sorted(available_datasets())}


@app.post("/model/train", response_model=TrainModelResponse)
async def train_credit_model(
    dataset: str | None = None,
    _: dict = Depends(require_admin),
) -> TrainModelResponse:
    try:
        dataset_path = resolve_dataset_key(dataset) if dataset else None
        result = train_model(dataset_path=dataset_path)
    except ModelTrainingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TrainModelResponse(**result.__dict__)


@app.post("/model/predict-risk", response_model=RiskPredictionResponse)
async def predict_credit_risk(
    payload: BorrowerProfileInput,
    _: dict = Depends(get_current_user),
) -> RiskPredictionResponse:
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
