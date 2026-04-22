from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import KFold, StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET_CANDIDATES = [
    PROJECT_ROOT / "1000bor.csv",
    PROJECT_ROOT / "credit_score_demo_100b_5yr.xlsx",
    PROJECT_ROOT / "credit_demo_dataset.xlsx",
]
ARTIFACT_DIR = Path(__file__).resolve().parents[1] / "artifacts"
MODEL_PATH = ARTIFACT_DIR / "credit_risk_model.joblib"
METRICS_PATH = ARTIFACT_DIR / "credit_risk_metrics.json"

BASE_PROFILE_COLUMNS = [
    "occupation",
    "sector",
    "age",
    "city",
    "state",
    "monthly_income_inr",
    "years_in_business",
    "has_gst",
    "has_formal_rent",
    "has_bank_account",
]
TARGET_COLUMN = "risk_category"
BOOLEAN_COLUMNS = ["has_gst", "has_formal_rent", "has_bank_account"]
SHEETS_FUSED = [
    "Borrower Profiles",
    "UPI Transactions",
    "GST Filings",
    "Rent & Utility",
    "Credit Decisions",
    "Summary Analytics",
    "Scoring Parameters",
]
FLAT_CSV_SOURCE = ["1000bor.csv (flat borrower dataset)"]


class ModelTrainingError(RuntimeError):
    pass


@dataclass
class TrainResult:
    records_used: int
    classes: list[str]
    metrics: dict[str, float]
    dataset_path: str
    sheets_fused: list[str]
    model_path: str
    metrics_path: str
    trained_at_utc: str


def _yes_no_to_bool(value: Any) -> bool | None:
    if pd.isna(value):
        return None
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"yes", "true", "1"}:
        return True
    if normalized in {"no", "false", "0"}:
        return False
    return None


def _normalize_borrower_id(value: Any) -> str:
    return str(value).strip().upper()


def _normalize_risk_label(value: Any) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip().lower().replace(" risk", "")
    if text in {"low", "medium", "high"}:
        return text
    return None


def _safe_to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _read_sheet_table(dataset_path: Path, sheet_name: str, header_key: str) -> pd.DataFrame:
    raw = pd.read_excel(dataset_path, sheet_name=sheet_name, header=None)
    header_matches = raw.index[raw.iloc[:, 0].astype(str).str.strip() == header_key]
    if len(header_matches) == 0:
        raise ModelTrainingError(f"Could not locate header row '{header_key}' in sheet '{sheet_name}'.")

    header_row = int(header_matches[0])
    headers = [
        str(value).strip() if not pd.isna(value) else f"unnamed_{index}"
        for index, value in enumerate(raw.iloc[header_row].tolist())
    ]
    table = raw.iloc[header_row + 1 :].copy()
    table.columns = headers
    table = table.dropna(how="all")
    return table


def resolve_dataset_path(dataset_path: Path | None = None) -> Path:
    if dataset_path is not None:
        resolved = dataset_path if dataset_path.is_absolute() else PROJECT_ROOT / dataset_path
        if resolved.exists():
            return resolved
        raise ModelTrainingError(f"Dataset file not found at '{resolved}'.")

    for candidate in DEFAULT_DATASET_CANDIDATES:
        if candidate.exists():
            return candidate

    names = ", ".join(path.name for path in DEFAULT_DATASET_CANDIDATES)
    raise ModelTrainingError(f"No supported dataset file found. Expected one of: {names}.")


def _load_profiles(dataset_path: Path) -> pd.DataFrame:
    table = _read_sheet_table(dataset_path, "Borrower Profiles", "Borrower ID")
    table = table.rename(
        columns={
            "Borrower ID": "borrower_id",
            "Full Name": "name",
            "Name": "name",
            "Occupation": "occupation",
            "Sector": "sector",
            "Age": "age",
            "City": "city",
            "State": "state",
            "Avg Monthly Income (₹)": "monthly_income_inr",
            "Monthly Income (₹)": "monthly_income_inr",
            "Years in Business": "years_in_business",
            "GST Registered": "has_gst",
            "Has GST": "has_gst",
            "Has Formal Rent": "has_formal_rent",
            "Has Bank Account": "has_bank_account",
            "Initial Risk Category": "initial_risk",
            "Risk Category": "initial_risk",
        }
    )
    required = ["borrower_id", *BASE_PROFILE_COLUMNS, "initial_risk"]
    missing = [column for column in required if column not in table.columns]
    if missing:
        raise ModelTrainingError(f"'Borrower Profiles' is missing columns: {', '.join(missing)}.")

    table["borrower_id"] = table["borrower_id"].apply(_normalize_borrower_id)
    table["age"] = _safe_to_numeric(table["age"])
    table["monthly_income_inr"] = _safe_to_numeric(table["monthly_income_inr"])
    table["years_in_business"] = _safe_to_numeric(table["years_in_business"])
    for column in BOOLEAN_COLUMNS:
        table[column] = table[column].apply(_yes_no_to_bool)
    table["initial_risk"] = table["initial_risk"].apply(_normalize_risk_label)

    return table.set_index("borrower_id")


def _load_upi_features(dataset_path: Path) -> pd.DataFrame:
    table = _read_sheet_table(dataset_path, "UPI Transactions", "Borrower ID")
    table = table.rename(
        columns={
            "Borrower ID": "borrower_id",
            "Total Inflow (₹)": "total_inflow_inr",
            "Total Outflow (₹)": "total_outflow_inr",
            "Net Cash Flow (₹)": "net_cash_flow_inr",
            "No. of Transactions": "transaction_count",
            "Merchant Count": "merchant_count",
            "Avg Transaction (₹)": "avg_transaction_inr",
            "Volatility Flag": "volatility_flag",
            "UPI Sub-Score (0-100)": "upi_sub_score",
        }
    )
    table["borrower_id"] = table["borrower_id"].apply(_normalize_borrower_id)
    for column in [
        "total_inflow_inr",
        "total_outflow_inr",
        "net_cash_flow_inr",
        "transaction_count",
        "merchant_count",
        "avg_transaction_inr",
        "upi_sub_score",
    ]:
        table[column] = _safe_to_numeric(table[column])
    table["volatility_flag"] = table["volatility_flag"].apply(_yes_no_to_bool)

    grouped = table.groupby("borrower_id")
    upi = grouped.agg(
        upi_inflow_mean=("total_inflow_inr", "mean"),
        upi_outflow_mean=("total_outflow_inr", "mean"),
        upi_net_cash_mean=("net_cash_flow_inr", "mean"),
        upi_net_cash_std=("net_cash_flow_inr", "std"),
        upi_txn_count_mean=("transaction_count", "mean"),
        upi_merchant_count_mean=("merchant_count", "mean"),
        upi_avg_transaction_mean=("avg_transaction_inr", "mean"),
        upi_sub_score_mean=("upi_sub_score", "mean"),
        upi_sub_score_std=("upi_sub_score", "std"),
        upi_volatility_rate=("volatility_flag", "mean"),
        upi_months_observed=("borrower_id", "count"),
    )
    upi["upi_net_cash_std"] = upi["upi_net_cash_std"].fillna(0)
    upi["upi_sub_score_std"] = upi["upi_sub_score_std"].fillna(0)
    return upi


def _load_gst_features(dataset_path: Path) -> pd.DataFrame:
    table = _read_sheet_table(dataset_path, "GST Filings", "Borrower ID")
    table = table.rename(
        columns={
            "Borrower ID": "borrower_id",
            "Filing Status": "filing_status",
            "Declared Turnover (₹)": "declared_turnover_inr",
            "Tax Paid (₹)": "tax_paid_inr",
            "Days Late": "days_late",
            "Penalty (₹)": "penalty_inr",
            "UPI vs GST Match %": "upi_gst_match_pct",
            "GST Sub-Score (0-100)": "gst_sub_score",
        }
    )
    table["borrower_id"] = table["borrower_id"].apply(_normalize_borrower_id)
    table["filing_status"] = table["filing_status"].astype(str).str.strip().str.lower()
    for column in ["declared_turnover_inr", "tax_paid_inr", "days_late", "penalty_inr", "upi_gst_match_pct", "gst_sub_score"]:
        table[column] = _safe_to_numeric(table[column])

    table["gst_filed_on_time"] = table["filing_status"].eq("filed on time").astype(int)
    table["gst_filed_late"] = table["filing_status"].eq("filed late").astype(int)
    table["gst_not_registered"] = table["filing_status"].eq("not registered").astype(int)

    gst = table.groupby("borrower_id").agg(
        gst_turnover_mean=("declared_turnover_inr", "mean"),
        gst_tax_paid_mean=("tax_paid_inr", "mean"),
        gst_days_late_mean=("days_late", "mean"),
        gst_penalty_sum=("penalty_inr", "sum"),
        gst_match_pct_mean=("upi_gst_match_pct", "mean"),
        gst_sub_score_mean=("gst_sub_score", "mean"),
        gst_filed_on_time_rate=("gst_filed_on_time", "mean"),
        gst_filed_late_rate=("gst_filed_late", "mean"),
        gst_not_registered_rate=("gst_not_registered", "mean"),
    )
    return gst


def _load_rent_utility_features(dataset_path: Path) -> pd.DataFrame:
    table = _read_sheet_table(dataset_path, "Rent & Utility", "Borrower ID")
    table = table.rename(
        columns={
            "Borrower ID": "borrower_id",
            "Rent Amount (₹)": "rent_amount_inr",
            "Rent Status": "rent_status",
            "Days Late (Rent)": "rent_days_late",
            "Electricity Bill (₹)": "electricity_bill_inr",
            "Electricity Status": "electricity_status",
            "Water Bill (₹)": "water_bill_inr",
            "Water Status": "water_status",
            "Stability Score (0-100)": "stability_sub_score",
        }
    )
    table["borrower_id"] = table["borrower_id"].apply(_normalize_borrower_id)
    table["rent_status"] = table["rent_status"].astype(str).str.strip().str.lower()
    table["electricity_status"] = table["electricity_status"].astype(str).str.strip().str.lower()
    table["water_status"] = table["water_status"].astype(str).str.strip().str.lower()
    for column in ["rent_amount_inr", "rent_days_late", "electricity_bill_inr", "water_bill_inr", "stability_sub_score"]:
        table[column] = _safe_to_numeric(table[column])

    table["rent_paid_on_time"] = table["rent_status"].eq("paid on time").astype(int)
    table["electricity_paid_on_time"] = table["electricity_status"].eq("paid on time").astype(int)
    table["water_paid_on_time"] = table["water_status"].eq("paid on time").astype(int)

    rent_utility = table.groupby("borrower_id").agg(
        rent_amount_mean=("rent_amount_inr", "mean"),
        rent_days_late_mean=("rent_days_late", "mean"),
        rent_on_time_rate=("rent_paid_on_time", "mean"),
        electricity_bill_mean=("electricity_bill_inr", "mean"),
        electricity_on_time_rate=("electricity_paid_on_time", "mean"),
        water_bill_mean=("water_bill_inr", "mean"),
        water_on_time_rate=("water_paid_on_time", "mean"),
        stability_sub_score_mean=("stability_sub_score", "mean"),
    )
    return rent_utility


def _load_credit_decision_features(dataset_path: Path) -> tuple[pd.DataFrame, pd.Series]:
    table = _read_sheet_table(dataset_path, "Credit Decisions", "Borrower ID")
    table = table.rename(
        columns={
            "Borrower ID": "borrower_id",
            "UPI Score (40%)": "decision_upi_score",
            "GST Score (25%)": "decision_gst_score",
            "Rent Score (20%)": "decision_rent_score",
            "Utility Score (15%)": "decision_utility_score",
            "Raw Score": "decision_raw_score",
            "Final Score (300-900)": "decision_final_score",
            "Confidence": "decision_confidence",
            "Risk Level": "decision_risk_level",
            "Recommended Loan (₹)": "decision_recommended_loan_inr",
            "Avg Monthly Income (₹)": "decision_avg_monthly_income_inr",
            "YoY Change": "decision_yoy_change",
            "Decision": "decision_outcome",
        }
    )
    table["borrower_id"] = table["borrower_id"].apply(_normalize_borrower_id)
    for column in [
        "decision_upi_score",
        "decision_gst_score",
        "decision_rent_score",
        "decision_utility_score",
        "decision_raw_score",
        "decision_final_score",
        "decision_confidence",
        "decision_recommended_loan_inr",
        "decision_avg_monthly_income_inr",
    ]:
        table[column] = _safe_to_numeric(table[column])

    table["decision_yoy_change"] = (
        table["decision_yoy_change"]
        .astype(str)
        .str.replace("+", "", regex=False)
        .str.replace("—", "", regex=False)
        .str.strip()
    )
    table["decision_yoy_change"] = _safe_to_numeric(table["decision_yoy_change"])
    table["risk_label"] = table["decision_risk_level"].apply(_normalize_risk_label)
    table["decision_outcome"] = table["decision_outcome"].astype(str).str.strip().str.lower()
    table["decision_approved"] = table["decision_outcome"].eq("approve").astype(int)
    table["decision_reviewed"] = table["decision_outcome"].eq("review").astype(int)
    table["decision_declined"] = table["decision_outcome"].eq("decline").astype(int)
    table["decision_risk_high"] = table["risk_label"].eq("high").astype(int)
    table["decision_risk_medium"] = table["risk_label"].eq("medium").astype(int)
    table["decision_risk_low"] = table["risk_label"].eq("low").astype(int)

    grouped = table.groupby("borrower_id")
    decision_features = grouped.agg(
        decision_upi_score_mean=("decision_upi_score", "mean"),
        decision_gst_score_mean=("decision_gst_score", "mean"),
        decision_rent_score_mean=("decision_rent_score", "mean"),
        decision_utility_score_mean=("decision_utility_score", "mean"),
        decision_raw_score_mean=("decision_raw_score", "mean"),
        decision_final_score_mean=("decision_final_score", "mean"),
        decision_final_score_std=("decision_final_score", "std"),
        decision_confidence_mean=("decision_confidence", "mean"),
        decision_recommended_loan_mean=("decision_recommended_loan_inr", "mean"),
        decision_yoy_change_mean=("decision_yoy_change", "mean"),
        decision_approval_rate=("decision_approved", "mean"),
        decision_review_rate=("decision_reviewed", "mean"),
        decision_decline_rate=("decision_declined", "mean"),
        decision_risk_high_rate=("decision_risk_high", "mean"),
        decision_risk_medium_rate=("decision_risk_medium", "mean"),
        decision_risk_low_rate=("decision_risk_low", "mean"),
    )
    decision_features["decision_final_score_std"] = decision_features["decision_final_score_std"].fillna(0)

    last_rows = grouped.tail(1).set_index("borrower_id")
    decision_features["decision_final_score_last"] = last_rows["decision_final_score"]
    decision_features["decision_confidence_last"] = last_rows["decision_confidence"]

    def _risk_severity(series: pd.Series) -> str:
        values = set(series.dropna().astype(str).tolist())
        if "high" in values:
            return "high"
        if "medium" in values:
            return "medium"
        return "low"

    decision_target = grouped["risk_label"].apply(_risk_severity).rename("decision_risk")
    return decision_features, decision_target


def _load_summary_constants(dataset_path: Path) -> dict[str, float]:
    table = _read_sheet_table(dataset_path, "Summary Analytics", "Year")
    table["Year"] = _safe_to_numeric(table["Year"])
    table["Avg Credit Score"] = _safe_to_numeric(table["Avg Credit Score"])
    table["Low Risk Count"] = _safe_to_numeric(table["Low Risk Count"])
    table["Medium Risk Count"] = _safe_to_numeric(table["Medium Risk Count"])
    table["High Risk Count"] = _safe_to_numeric(table["High Risk Count"])
    table["Approval Rate %"] = _safe_to_numeric(table["Approval Rate %"])
    table = table.dropna(subset=["Year", "Avg Credit Score", "Approval Rate %"])
    table = table.sort_values("Year")
    if table.empty:
        return {}

    total_risk = table["Low Risk Count"] + table["Medium Risk Count"] + table["High Risk Count"]
    high_risk_share = (table["High Risk Count"] / total_risk).fillna(0)
    return {
        "portfolio_avg_credit_score_mean": float(table["Avg Credit Score"].mean()),
        "portfolio_avg_credit_score_trend": float(table["Avg Credit Score"].iloc[-1] - table["Avg Credit Score"].iloc[0]),
        "portfolio_approval_rate_mean": float(table["Approval Rate %"].mean()),
        "portfolio_approval_rate_trend": float(table["Approval Rate %"].iloc[-1] - table["Approval Rate %"].iloc[0]),
        "portfolio_high_risk_share_mean": float(high_risk_share.mean()),
    }


def _load_scoring_parameter_constants(dataset_path: Path) -> dict[str, float]:
    table = _read_sheet_table(dataset_path, "Scoring Parameters", "Agent Weights")
    if table.empty:
        return {}

    first_four = table.columns.tolist()[:4]
    rename_map = {
        first_four[0]: "agent_name",
        first_four[1]: "weight_pct",
        first_four[2]: "signal_rationale",
        first_four[3]: "compliance_note",
    }
    table = table.rename(columns=rename_map)
    table["agent_name"] = table["agent_name"].astype(str).str.strip().str.lower()
    table["weight_pct"] = (
        table["weight_pct"].astype(str).str.replace("%", "", regex=False).str.replace(" ", "", regex=False).str.strip()
    )
    table["weight_pct"] = _safe_to_numeric(table["weight_pct"]) / 100.0
    table = table.dropna(subset=["weight_pct"])

    constants: dict[str, float] = {}
    for _, row in table.iterrows():
        agent_name = str(row["agent_name"])
        weight = float(row["weight_pct"])
        if "upi" in agent_name:
            constants["weight_upi_agent"] = weight
        elif "gst" in agent_name:
            constants["weight_gst_agent"] = weight
        elif "rent" in agent_name:
            constants["weight_rent_agent"] = weight
        elif "utility" in agent_name:
            constants["weight_utility_agent"] = weight

    if constants:
        constants["weight_total"] = float(sum(constants.values()))
    return constants


def _normalize_loan_decision(value: Any) -> str:
    text = str(value).strip().lower()
    if text in {"approved", "approve"}:
        return "approved"
    if text in {"conditionally approved", "conditional", "conditionally-approved"}:
        return "conditionally_approved"
    if text in {"under review", "review"}:
        return "under_review"
    if text in {"rejected", "declined", "decline"}:
        return "rejected"
    return "under_review"


def _risk_from_decision_and_score(decision: str, credit_score: float | int | None) -> str:
    normalized_decision = _normalize_loan_decision(decision)
    numeric_score = float(credit_score) if credit_score is not None and not pd.isna(credit_score) else np.nan

    if normalized_decision == "approved":
        if not pd.isna(numeric_score) and numeric_score < 620:
            return "medium"
        return "low"
    if normalized_decision in {"conditionally_approved", "under_review"}:
        if not pd.isna(numeric_score) and numeric_score >= 760:
            return "low"
        if not pd.isna(numeric_score) and numeric_score < 560:
            return "high"
        return "medium"
    return "high"


def _load_flat_csv_dataset(dataset_path: Path) -> pd.DataFrame:
    df = pd.read_csv(dataset_path)
    required = [
        "age",
        "state",
        "employment_type",
        "work_experience_years",
        "monthly_income_inr",
        "credit_score",
        "loan_decision",
    ]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ModelTrainingError(
            f"CSV dataset '{dataset_path.name}' is missing required columns: {', '.join(missing)}."
        )

    # Keep model-serving compatibility with BorrowerProfileInput by exposing the baseline profile fields.
    df["occupation"] = df["employment_type"].astype(str).str.strip()
    df["sector"] = df.get("loan_purpose", df["employment_type"]).astype(str).str.strip()
    df["city"] = df["state"].astype(str).str.strip()
    df["years_in_business"] = _safe_to_numeric(df["work_experience_years"])
    df["has_gst"] = df.get("gst_filed_regularly", 0)
    df["has_formal_rent"] = (
        df.get("residence_type", "unknown").astype(str).str.strip().str.lower().eq("rented").astype(int)
    )
    df["has_bank_account"] = (_safe_to_numeric(df.get("bank_balance_avg_3m_inr", 0)) > 0).astype(int)

    numeric_candidates = [
        "age",
        "num_dependents",
        "work_experience_years",
        "monthly_income_inr",
        "bank_balance_avg_3m_inr",
        "savings_rate_pct",
        "upi_monthly_txn_count",
        "upi_monthly_txn_value_inr",
        "mobile_bill_ontime_pct",
        "utility_bill_ontime_pct",
        "credit_history_months",
        "num_credit_accounts",
        "credit_mix_score",
        "credit_utilization_pct",
        "num_hard_inquiries_12m",
        "num_missed_payments_24m",
        "num_defaults",
        "existing_active_loans",
        "loan_amount_requested_inr",
        "loan_tenure_months",
        "estimated_emi_inr",
        "debt_to_income_ratio",
        "credit_score",
        "interest_rate_pct",
        "years_in_business",
    ]
    for column in numeric_candidates:
        if column in df.columns:
            df[column] = _safe_to_numeric(df[column])

    bool_candidates = [
        "has_credit_card",
        "has_secured_loan",
        "gst_filed_regularly",
        "has_gst",
        "has_formal_rent",
        "has_bank_account",
    ]
    for column in bool_candidates:
        if column in df.columns:
            df[column] = df[column].apply(_yes_no_to_bool)

    df[TARGET_COLUMN] = [
        _risk_from_decision_and_score(decision=value_decision, credit_score=value_score)
        for value_decision, value_score in zip(df["loan_decision"], df.get("credit_score"))
    ]
    df[TARGET_COLUMN] = df[TARGET_COLUMN].apply(_normalize_risk_label)

    required_not_null = [
        "occupation",
        "sector",
        "age",
        "city",
        "state",
        "monthly_income_inr",
        "years_in_business",
        TARGET_COLUMN,
    ]
    df = df.dropna(subset=required_not_null)
    if df.empty:
        raise ModelTrainingError(
            f"CSV dataset '{dataset_path.name}' contains no usable records after cleaning."
        )

    if "applicant_id" in df.columns:
        df["applicant_id"] = df["applicant_id"].apply(_normalize_borrower_id)

    return df


def _sources_for_dataset(dataset_path: Path) -> list[str]:
    if dataset_path.suffix.lower() == ".csv":
        return FLAT_CSV_SOURCE
    return SHEETS_FUSED


def load_dataset(dataset_path: Path | None = None) -> pd.DataFrame:
    resolved_path = resolve_dataset_path(dataset_path)
    if resolved_path.suffix.lower() == ".csv":
        return _load_flat_csv_dataset(resolved_path)

    profiles = _load_profiles(resolved_path)
    upi = _load_upi_features(resolved_path)
    gst = _load_gst_features(resolved_path)
    rent_utility = _load_rent_utility_features(resolved_path)
    decisions, decision_target = _load_credit_decision_features(resolved_path)
    summary_constants = _load_summary_constants(resolved_path)
    scoring_constants = _load_scoring_parameter_constants(resolved_path)

    fused = profiles.join(upi, how="left")
    fused = fused.join(gst, how="left")
    fused = fused.join(rent_utility, how="left")
    fused = fused.join(decisions, how="left")
    fused = fused.join(decision_target, how="left")

    for key, value in {**summary_constants, **scoring_constants}.items():
        fused[key] = value

    fused[TARGET_COLUMN] = fused["decision_risk"].where(fused["decision_risk"].notna(), fused["initial_risk"])
    fused[TARGET_COLUMN] = fused[TARGET_COLUMN].apply(_normalize_risk_label)
    fused = fused.drop(columns=["decision_risk", "name"], errors="ignore")

    required_columns = ["occupation", "age", "city", "state", "monthly_income_inr", "years_in_business", TARGET_COLUMN]
    fused = fused.dropna(subset=required_columns)
    if fused.empty:
        raise ModelTrainingError("Dataset contains no usable fused rows after cleaning.")

    return fused


def _build_pipeline(numeric_columns: list[str], categorical_columns: list[str]) -> Pipeline:
    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )

    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_columns),
            ("cat", categorical_transformer, categorical_columns),
        ]
    )

    model = RandomForestClassifier(
        n_estimators=250,
        max_depth=8,
        random_state=42,
        class_weight="balanced_subsample",
    )

    return Pipeline(steps=[("preprocessor", preprocessor), ("model", model)])


def train_model(dataset_path: Path | None = None) -> TrainResult:
    resolved_dataset_path = resolve_dataset_path(dataset_path)
    sources_used = _sources_for_dataset(resolved_dataset_path)
    df = load_dataset(resolved_dataset_path)
    y = df[TARGET_COLUMN].copy()
    x = df.drop(columns=[TARGET_COLUMN, "initial_risk"], errors="ignore").copy()

    for column in BOOLEAN_COLUMNS:
        if column in x.columns:
            x[column] = x[column].apply(_yes_no_to_bool).map({True: 1, False: 0})

    feature_columns = list(x.columns)
    numeric_columns = [column for column in feature_columns if pd.api.types.is_numeric_dtype(x[column])]
    categorical_columns = [column for column in feature_columns if column not in numeric_columns]
    if not feature_columns:
        raise ModelTrainingError("No training features available after data fusion.")
    if not numeric_columns and not categorical_columns:
        raise ModelTrainingError("Unable to infer feature types for training.")

    class_counts = y.value_counts()
    if len(class_counts) < 2:
        raise ModelTrainingError("Training requires at least two risk classes.")
    if len(df) < 6:
        raise ModelTrainingError("Dataset is too small for reliable training. Need at least 6 usable records.")

    pipeline = _build_pipeline(numeric_columns=numeric_columns, categorical_columns=categorical_columns)
    can_stratify = class_counts.min() >= 2
    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.25,
        random_state=42,
        stratify=y if can_stratify else None,
    )

    pipeline.fit(x_train, y_train)
    y_pred = pipeline.predict(x_test)

    if can_stratify:
        fold_count = min(3, int(class_counts.min()))
        cv_strategy = StratifiedKFold(n_splits=fold_count, shuffle=True, random_state=42)
    else:
        fold_count = min(3, len(df))
        cv_strategy = KFold(n_splits=fold_count, shuffle=True, random_state=42)

    cv_scores = cross_val_score(
        _build_pipeline(numeric_columns=numeric_columns, categorical_columns=categorical_columns),
        x,
        y,
        cv=cv_strategy,
        scoring="accuracy",
    )

    pipeline.fit(x, y)

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    trained_at = datetime.now(timezone.utc).isoformat()
    artifact = {
        "pipeline": pipeline,
        "feature_columns": feature_columns,
        "boolean_columns": BOOLEAN_COLUMNS,
        "numeric_columns": numeric_columns,
        "categorical_columns": categorical_columns,
        "classes": sorted(y.unique().tolist()),
        "dataset_path": str(resolved_dataset_path),
        "sheets_fused": sources_used,
        "trained_at_utc": trained_at,
    }
    joblib.dump(artifact, MODEL_PATH)

    metrics = {
        "holdout_accuracy": float(accuracy_score(y_test, y_pred)),
        "holdout_macro_f1": float(f1_score(y_test, y_pred, average="macro", zero_division=0)),
        "cross_val_accuracy_mean": float(cv_scores.mean()),
        "cross_val_accuracy_std": float(cv_scores.std()),
    }
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    return TrainResult(
        records_used=len(df),
        classes=sorted(y.unique().tolist()),
        metrics=metrics,
        dataset_path=str(resolved_dataset_path),
        sheets_fused=sources_used,
        model_path=str(MODEL_PATH),
        metrics_path=str(METRICS_PATH),
        trained_at_utc=trained_at,
    )


def model_is_trained() -> bool:
    return MODEL_PATH.exists()


def predict_risk(profile: dict[str, Any]) -> tuple[str, dict[str, float], str]:
    if not MODEL_PATH.exists():
        raise ModelTrainingError("Model is not trained yet. Call /model/train first.")

    artifact: dict[str, Any] = joblib.load(MODEL_PATH)
    pipeline: Pipeline = artifact["pipeline"]
    feature_columns: list[str] = artifact["feature_columns"]
    bool_columns: list[str] = artifact["boolean_columns"]
    trained_at: str = artifact["trained_at_utc"]

    row = {column: profile.get(column, np.nan) for column in feature_columns}
    df = pd.DataFrame([row])

    for column in bool_columns:
        if column not in df.columns:
            continue
        df[column] = df[column].apply(_yes_no_to_bool).map({True: 1, False: 0})
        df[column] = pd.to_numeric(df[column], errors="coerce")

    predicted_label = str(pipeline.predict(df)[0])
    probabilities = pipeline.predict_proba(df)[0]
    classes = [str(label) for label in pipeline.classes_]
    probability_map = {label: round(float(prob), 4) for label, prob in zip(classes, probabilities)}

    return predicted_label, probability_map, trained_at
