from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import pandas as pd

from .schemas import SignalType

SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}

NumericLike = float | int | str | bool


@dataclass
class StatementDerivation:
    derived_fields: dict[str, NumericLike]
    summary: str
    rows_processed: int


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _normalize_column_name(value: str) -> str:
    normalized = "".join(ch.lower() if ch.isalnum() else "_" for ch in value.strip())
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return normalized.strip("_")


def _normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    renamed = frame.copy()
    renamed.columns = [_normalize_column_name(str(col)) for col in renamed.columns]
    return renamed


def _find_column(columns: list[str], *candidates: str) -> str | None:
    for candidate in candidates:
        if candidate in columns:
            return candidate
    for candidate in candidates:
        for column in columns:
            if candidate in column:
                return column
    return None


def _to_numeric(series: pd.Series) -> pd.Series:
    cleaned = series.astype(str).str.replace(r"[^\d\.\-]", "", regex=True)
    return pd.to_numeric(cleaned, errors="coerce")


def _to_datetime(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce", dayfirst=True)


def _prepare_monthly_trend(monthly_values: pd.Series) -> float:
    if monthly_values.empty:
        return 0.0
    window = min(3, len(monthly_values))
    first_avg = float(monthly_values.head(window).mean())
    last_avg = float(monthly_values.tail(window).mean())
    if first_avg <= 0:
        return 100.0 if last_avg > 0 else 0.0
    return ((last_avg - first_avg) / first_avg) * 100.0


def _longest_month_gap(date_series: pd.Series) -> int:
    if date_series.empty:
        return 0
    periods = sorted(date_series.dt.to_period("M").unique())
    if len(periods) <= 1:
        return 0

    longest = 0
    for previous, current in zip(periods, periods[1:]):
        gap = int(current - previous) - 1
        longest = max(longest, gap)
    return max(0, longest)


def _read_statement_frame(filename: str, content: bytes) -> pd.DataFrame:
    extension = Path(filename or "").suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError("Unsupported file type. Please upload CSV or Excel statements.")

    if extension == ".csv":
        try:
            frame = pd.read_csv(BytesIO(content))
        except UnicodeDecodeError:
            frame = pd.read_csv(BytesIO(content), encoding="latin-1")
    else:
        frame = pd.read_excel(BytesIO(content))

    frame = frame.dropna(how="all")
    if frame.empty:
        raise ValueError("Statement file is empty.")
    return _normalize_columns(frame)


def _derive_upi_signals(frame: pd.DataFrame) -> StatementDerivation:
    columns = frame.columns.tolist()
    date_col = _find_column(columns, "transaction_date", "txn_date", "date", "timestamp", "created_at")
    amount_col = _find_column(columns, "amount", "transaction_amount", "txn_amount", "amount_inr", "value")
    merchant_col = _find_column(columns, "merchant", "payee", "counterparty", "description", "narration", "remarks")

    if not date_col or not amount_col:
        raise ValueError("UPI statement must include transaction date and amount columns.")

    working = pd.DataFrame(
        {
            "date": _to_datetime(frame[date_col]),
            "amount": _to_numeric(frame[amount_col]).abs(),
        }
    )
    if merchant_col:
        working["merchant"] = frame[merchant_col].astype(str)
    else:
        working["merchant"] = ""

    working = working.dropna(subset=["date", "amount"])
    working = working[working["amount"] > 0]
    if working.empty:
        raise ValueError("No valid transactions found in the uploaded UPI statement.")

    working["month"] = working["date"].dt.to_period("M").dt.to_timestamp()
    monthly = working.groupby("month", as_index=False).agg(
        transaction_count=("amount", "size"),
        transaction_volume=("amount", "sum"),
    )
    months_of_history = int(monthly.shape[0])
    transaction_frequency = int(round(len(working) / max(1, months_of_history)))
    average_transaction_value = float(working["amount"].mean())

    merchants = (
        working["merchant"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )
    unique_merchants = int(merchants[merchants.str.len() > 0].nunique())
    merchant_diversity = _clamp(unique_merchants / max(1, min(len(working), 25)), 0.0, 1.0)

    monthly_counts = monthly["transaction_count"]
    if months_of_history <= 1:
        regularity = 1.0
    else:
        mean_count = float(monthly_counts.mean())
        std_count = float(monthly_counts.std(ddof=0))
        regularity = _clamp(1.0 - (std_count / max(mean_count, 1.0)), 0.0, 1.0)

    trend_pct = _clamp(_prepare_monthly_trend(monthly["transaction_volume"]), -100.0, 300.0)

    return StatementDerivation(
        derived_fields={
            "transaction_frequency_per_month": transaction_frequency,
            "average_transaction_value_inr": round(average_transaction_value, 2),
            "merchant_diversity_score": round(merchant_diversity, 2),
            "regularity_score": round(regularity, 2),
            "months_of_history": months_of_history,
            "monthly_volume_trend_pct": round(trend_pct, 2),
        },
        summary=(
            f"Derived UPI metrics from {len(working)} transactions across {months_of_history} month(s)."
        ),
        rows_processed=int(len(working)),
    )


def _derive_gst_signals(frame: pd.DataFrame) -> StatementDerivation:
    columns = frame.columns.tolist()
    filing_date_col = _find_column(
        columns, "filing_date", "filed_on", "return_filed_on", "date", "tax_period", "period"
    )
    due_date_col = _find_column(columns, "due_date", "return_due_date", "deadline")
    status_col = _find_column(columns, "status", "filing_status", "return_status")
    revenue_col = _find_column(columns, "revenue", "turnover", "taxable_value", "sales", "gross_value")

    if not filing_date_col:
        raise ValueError("GST statement must include a filing date or return period column.")

    working = pd.DataFrame({"filing_date": _to_datetime(frame[filing_date_col])})
    working = working.dropna(subset=["filing_date"])
    if working.empty:
        raise ValueError("No valid GST filing dates were found in the uploaded statement.")

    if due_date_col:
        working["due_date"] = _to_datetime(frame[due_date_col])
    if status_col:
        working["status"] = frame[status_col].astype(str).str.strip().str.lower()
    if revenue_col:
        working["revenue"] = _to_numeric(frame[revenue_col])
    else:
        working["revenue"] = 0.0

    working = working.sort_values("filing_date")
    gaps = working["filing_date"].diff().dt.days.dropna()
    median_gap_days = float(gaps.median()) if not gaps.empty else 30.0
    filing_frequency = "quarterly" if median_gap_days > 50 else "monthly"
    expected_filings = 4 if filing_frequency == "quarterly" else 12

    latest_date = working["filing_date"].max()
    horizon_start = latest_date - pd.Timedelta(days=365)
    last_12m = working[working["filing_date"] >= horizon_start]
    filed_count_last_12m = int(last_12m.shape[0])
    gap_based_missed = max(0, expected_filings - filed_count_last_12m)

    status_based_missed = 0
    if "status" in last_12m:
        status_based_missed = int(
            last_12m["status"].str.contains("miss|default|not filed|pending", regex=True, na=False).sum()
        )

    late_count = 0
    if "due_date" in last_12m:
        due_valid = last_12m.dropna(subset=["due_date"])
        late_count = int((due_valid["filing_date"] > due_valid["due_date"]).sum())

    missed_filings = max(gap_based_missed, status_based_missed)
    filing_consistency = _clamp(1.0 - ((missed_filings + (late_count * 0.5)) / max(expected_filings, 1)), 0.0, 1.0)

    revenue_rows = working[working["revenue"].notna() & (working["revenue"] >= 0)].copy()
    if revenue_rows.empty:
        revenue_trend_pct = 0.0
    else:
        revenue_rows["month"] = revenue_rows["filing_date"].dt.to_period("M").dt.to_timestamp()
        monthly_revenue = revenue_rows.groupby("month")["revenue"].sum()
        revenue_trend_pct = _clamp(_prepare_monthly_trend(monthly_revenue), -100.0, 300.0)

    return StatementDerivation(
        derived_fields={
            "filing_frequency": filing_frequency,
            "filing_consistency_score": round(filing_consistency, 2),
            "missed_filings_last_12m": int(missed_filings),
            "revenue_trend_pct": round(revenue_trend_pct, 2),
            "is_applicable": True,
        },
        summary=(
            f"Derived GST compliance metrics from {len(working)} filing row(s), inferred as {filing_frequency}."
        ),
        rows_processed=int(len(working)),
    )


def _derive_rent_signals(frame: pd.DataFrame) -> StatementDerivation:
    columns = frame.columns.tolist()
    date_col = _find_column(columns, "payment_date", "transaction_date", "txn_date", "date", "paid_on")
    amount_col = _find_column(columns, "amount", "rent_amount", "transaction_amount", "value")
    due_date_col = _find_column(columns, "due_date", "rent_due_date")
    status_col = _find_column(columns, "status", "payment_status")

    if not date_col or not amount_col:
        raise ValueError("Rent statement must include payment date and amount columns.")

    working = pd.DataFrame(
        {
            "payment_date": _to_datetime(frame[date_col]),
            "amount": _to_numeric(frame[amount_col]).abs(),
        }
    )
    if due_date_col:
        working["due_date"] = _to_datetime(frame[due_date_col])
    if status_col:
        working["status"] = frame[status_col].astype(str).str.strip().str.lower()

    working = working.dropna(subset=["payment_date", "amount"])
    working = working[working["amount"] > 0]
    if working.empty:
        raise ValueError("No valid rent payment rows were found in the uploaded statement.")

    if "due_date" in working:
        valid_due = working["due_date"].notna()
        on_time_mask = pd.Series(True, index=working.index)
        on_time_mask[valid_due] = working.loc[valid_due, "payment_date"] <= working.loc[valid_due, "due_date"]
    elif "status" in working:
        on_time_mask = ~working["status"].str.contains("late|delay|overdue|miss", regex=True, na=False)
    else:
        on_time_mask = working["payment_date"].dt.day <= 10

    latest_date = working["payment_date"].max()
    horizon_start = latest_date - pd.Timedelta(days=730)
    last_24m_mask = working["payment_date"] >= horizon_start
    late_last_24m = int((~on_time_mask[last_24m_mask]).sum())

    tenancy_months = int(working["payment_date"].dt.to_period("M").nunique())
    longest_gap = _longest_month_gap(working["payment_date"])
    monthly_rent = float(
        working.assign(month=working["payment_date"].dt.to_period("M").dt.to_timestamp())
        .groupby("month")["amount"]
        .sum()
        .median()
    )
    on_time_ratio = _clamp(float(on_time_mask.mean()), 0.0, 1.0)

    return StatementDerivation(
        derived_fields={
            "rent_amount_inr": round(monthly_rent, 2),
            "on_time_payment_ratio": round(on_time_ratio, 2),
            "late_payments_last_24m": late_last_24m,
            "tenancy_months": tenancy_months,
            "longest_gap_months": longest_gap,
        },
        summary=f"Derived rent payment metrics from {len(working)} payment row(s).",
        rows_processed=int(len(working)),
    )


def _derive_utility_signals(frame: pd.DataFrame) -> StatementDerivation:
    columns = frame.columns.tolist()
    date_col = _find_column(columns, "payment_date", "transaction_date", "txn_date", "date")
    amount_col = _find_column(columns, "amount", "bill_amount", "transaction_amount", "value")
    status_col = _find_column(columns, "status", "payment_status")
    category_col = _find_column(columns, "category", "bill_type", "utility_type", "provider", "description", "narration")
    due_date_col = _find_column(columns, "due_date", "bill_due_date")

    if not date_col or not amount_col:
        raise ValueError("Utility statement must include payment date and amount columns.")

    working = pd.DataFrame(
        {
            "payment_date": _to_datetime(frame[date_col]),
            "amount": _to_numeric(frame[amount_col]).abs(),
        }
    )
    if status_col:
        working["status"] = frame[status_col].astype(str).str.strip().str.lower()
    if category_col:
        working["category"] = frame[category_col].astype(str).str.strip().str.lower()
    else:
        working["category"] = ""
    if due_date_col:
        working["due_date"] = _to_datetime(frame[due_date_col])

    working = working.dropna(subset=["payment_date", "amount"])
    working = working[working["amount"] > 0]
    if working.empty:
        raise ValueError("No valid utility payment rows were found in the uploaded statement.")

    if "due_date" in working:
        valid_due = working["due_date"].notna()
        on_time_mask = pd.Series(True, index=working.index)
        on_time_mask[valid_due] = working.loc[valid_due, "payment_date"] <= working.loc[valid_due, "due_date"]
    elif "status" in working:
        on_time_mask = ~working["status"].str.contains("late|delay|overdue|miss", regex=True, na=False)
    else:
        on_time_mask = working["payment_date"].dt.day <= 12

    categories = working["category"].fillna("").astype(str)
    electricity_mask = categories.str.contains("electric|power|bijli|eb", regex=True)
    water_mask = categories.str.contains("water|jal", regex=True)

    overall_ratio = _clamp(float(on_time_mask.mean()), 0.0, 1.0)
    if electricity_mask.any():
        electricity_ratio = _clamp(float(on_time_mask[electricity_mask].mean()), 0.0, 1.0)
    else:
        electricity_ratio = overall_ratio
    if water_mask.any():
        water_ratio = _clamp(float(on_time_mask[water_mask].mean()), 0.0, 1.0)
    else:
        water_ratio = overall_ratio

    monthly_totals = (
        working.assign(month=working["payment_date"].dt.to_period("M").dt.to_timestamp())
        .groupby("month")["amount"]
        .sum()
    )

    return StatementDerivation(
        derived_fields={
            "electricity_on_time_ratio": round(electricity_ratio, 2),
            "water_on_time_ratio": round(water_ratio, 2),
            "average_monthly_total_inr": round(float(monthly_totals.mean()), 2),
            "payment_months_observed": int(monthly_totals.shape[0]),
        },
        summary=f"Derived utility payment metrics from {len(working)} row(s).",
        rows_processed=int(len(working)),
    )


def _derive_employment_signals(frame: pd.DataFrame) -> StatementDerivation:
    columns = frame.columns.tolist()
    date_col = _find_column(columns, "transaction_date", "txn_date", "date", "value_date", "posted_on")
    amount_col = _find_column(columns, "amount", "transaction_amount", "txn_amount", "value")
    type_col = _find_column(columns, "type", "dr_cr", "credit_debit", "transaction_type")
    description_col = _find_column(columns, "description", "narration", "remarks", "counterparty", "merchant")

    if not date_col or not amount_col:
        raise ValueError("Employment statement must include transaction date and amount columns.")

    working = pd.DataFrame(
        {
            "date": _to_datetime(frame[date_col]),
            "raw_amount": _to_numeric(frame[amount_col]),
        }
    )
    working = working.dropna(subset=["date", "raw_amount"])
    if working.empty:
        raise ValueError("No valid income rows were found in the uploaded employment statement.")

    if description_col:
        working["description"] = (
            frame.loc[working.index, description_col].fillna("").astype(str).str.lower()
        )
    else:
        working["description"] = ""

    amount = working["raw_amount"].copy()
    if type_col:
        tx_type = frame.loc[working.index, type_col].fillna("").astype(str).str.strip().str.lower()
        is_credit = tx_type.str.contains("cr|credit|inflow|deposit", regex=True)
        is_debit = tx_type.str.contains("dr|debit|outflow|withdraw", regex=True)
        signed_amount = amount.abs()
        signed_amount[is_debit] = -signed_amount[is_debit]
        signed_amount[is_credit] = signed_amount[is_credit]
        working["amount"] = signed_amount
    else:
        working["amount"] = amount

    income_keywords = "salary|payroll|invoice|client|payout|consult|freelance|settlement|stipend"
    income_like = working["description"].str.contains(income_keywords, regex=True, na=False)
    positive_inflows = working["amount"] > 0
    income_rows = working[positive_inflows & (income_like | (working["description"].str.len() == 0))]
    if income_rows.empty:
        income_rows = working[positive_inflows]
    if income_rows.empty:
        raise ValueError("No credit inflows were found to derive employment signals.")

    income_rows = income_rows.assign(month=income_rows["date"].dt.to_period("M").dt.to_timestamp())
    monthly_income = income_rows.groupby("month")["amount"].sum()
    months_in_work = int(monthly_income.shape[0])
    avg_monthly_income = float(monthly_income.mean())
    income_std = float(monthly_income.std(ddof=0)) if months_in_work > 1 else 0.0
    stability = _clamp(1.0 - (income_std / max(avg_monthly_income, 1.0)), 0.0, 1.0)

    salary_hits = int(income_rows["description"].str.contains("salary|payroll", regex=True, na=False).sum())
    freelance_hits = int(
        income_rows["description"].str.contains("invoice|freelance|consult|client", regex=True, na=False).sum()
    )
    if salary_hits >= max(1, freelance_hits) and salary_hits >= (len(income_rows) * 0.35):
        employment_type = "salaried"
    elif freelance_hits > salary_hits:
        employment_type = "freelance"
    else:
        employment_type = "self_employed"

    return StatementDerivation(
        derived_fields={
            "employment_type": employment_type,
            "monthly_income_inr": round(avg_monthly_income, 2),
            "income_stability_score": round(stability, 2),
            "months_in_current_work": months_in_work,
            "income_proof_type": "bank_statement",
        },
        summary=f"Derived employment metrics from {len(income_rows)} qualifying inflow row(s).",
        rows_processed=int(len(income_rows)),
    )


def derive_signals_from_statement(signal_type: SignalType, filename: str, content: bytes) -> StatementDerivation:
    frame = _read_statement_frame(filename=filename, content=content)
    if signal_type == "upi":
        return _derive_upi_signals(frame)
    if signal_type == "gst":
        return _derive_gst_signals(frame)
    if signal_type == "rent":
        return _derive_rent_signals(frame)
    if signal_type == "utilities":
        return _derive_utility_signals(frame)
    if signal_type == "employment":
        return _derive_employment_signals(frame)

    raise ValueError(f"Unsupported signal type '{signal_type}'.")
