from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .agents import get_orchestration_status, run_all_agents
from .auth import (
    AuthError,
    authenticate,
    create_access_token,
    create_user,
    init_db,
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

@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Cred-ible Scoring API",
    version="0.1.0",
    description="Dynamic alternative credit scoring API for credit-invisible borrowers.",
    lifespan=lifespan,
)


def _allowed_origins() -> list[str]:
    configured = os.getenv("CREDIBLE_ALLOWED_ORIGINS", "")
    if configured.strip():
        return [origin.strip().rstrip("/") for origin in configured.split(",") if origin.strip()]

    return [
        "https://cred-ible.vercel.app",
        "https://www.cred-ible.vercel.app",
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ]

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


def _auth_response(user: dict, message: str) -> AuthResponse:
    token, ttl = create_access_token(user)
    return AuthResponse(
        user_id=user["id"],
        full_name=user["full_name"],
        work_email=user["email"],
        organization=user["organization"],
        role=user["role"],
        session_token=token,
        expires_in_seconds=ttl,
        message=message,
    )


@app.post("/auth/login", response_model=AuthResponse)
async def login(payload: LoginRequest) -> AuthResponse:
    user = authenticate(payload.email, payload.password)
    if user is None:
        # One message for both "no such account" and "wrong password", so the
        # endpoint cannot be used to enumerate registered emails.
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    return _auth_response(user, "Signed in successfully.")


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
    return _auth_response(user, "Workspace account created successfully.")


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
    return get_marketplace_offers(score)


@app.get("/model/status")
async def model_status() -> dict[str, bool]:
    return {"trained": model_is_trained()}


@app.get("/model/datasets")
async def list_trainable_datasets(_: dict = Depends(require_admin)) -> dict:
    """Dataset names accepted by `/model/train`. Admin-only, like training."""
    return {"datasets": sorted(available_datasets())}


@app.post("/model/train", response_model=TrainModelResponse)
async def train_credit_model(
    dataset: str | None = None,
    _: dict = Depends(require_admin),
) -> TrainModelResponse:
    """Retrain the risk model. Admin-only.

    `dataset` is a name from `/model/datasets`, not a path. Retraining
    overwrites the artifact every scoring request reads, so this must never be
    reachable unauthenticated, and the caller must never be able to choose an
    arbitrary file on the host.
    """
    try:
        dataset_path = resolve_dataset_key(dataset) if dataset else None
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
