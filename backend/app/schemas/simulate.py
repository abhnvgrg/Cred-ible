from __future__ import annotations

from pydantic import BaseModel, Field


class SimulationSignals(BaseModel):
    upi_monthly_txn_count: int = Field(ge=0, le=5000)
    utility_bill_ontime_pct: float = Field(ge=0, le=100)
    savings_rate_pct: float = Field(ge=-100, le=100)
    months_of_history: int = Field(ge=0, le=120)
    debt_to_income_ratio: float = Field(ge=0, le=5)
    gst_compliance_score: float = Field(ge=0, le=1)


class ScoreSimulationRequest(BaseModel):
    current_signals: SimulationSignals
    projected_signals: SimulationSignals
    baseline_score: int | None = Field(default=None, ge=300, le=900)


class AgentDeltas(BaseModel):
    income_agent: int
    repayment_agent: int
    lifestyle_agent: int
    compliance_agent: int


class ScoreSimulationResponse(BaseModel):
    baseline_score: int = Field(ge=300, le=900)
    projected_score: int = Field(ge=300, le=900)
    delta: int
    top_improvement: str
    explanation: str
    agent_deltas: AgentDeltas
    confidence: float = Field(ge=0, le=1)
