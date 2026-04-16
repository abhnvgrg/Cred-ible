from __future__ import annotations

import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .agents import run_all_agents
from .experience import (
    authenticate_user,
    get_marketplace_offers,
    register_user,
    run_what_if_simulation,
)
from .fixtures import load_personas
from .ml_model import ModelTrainingError, model_is_trained, predict_risk, train_model
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
    TrainModelResponse,
    WhatIfRequest,
    WhatIfResponse,
)

app = FastAPI(
    title="Cred-ible Scoring API",
    version="0.1.0",
    description="Dynamic alternative credit scoring API for credit-invisible borrowers.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://cred-ible.vercel.app"
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.post("/simulate/what-if", response_model=WhatIfResponse)
async def what_if(payload: WhatIfRequest) -> WhatIfResponse:
    return run_what_if_simulation(payload)


@app.get("/marketplace/offers", response_model=MarketplaceResponse)
async def marketplace_offers(score: int = 714) -> MarketplaceResponse:
    return get_marketplace_offers(score)


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
