from __future__ import annotations

"""
Signal Derivation Layer
========================
Pure functions — no I/O, no file access, no side effects.

Takes a list of ParsedTransaction objects and a borrower name,
returns a DerivedSignalResult containing the 14 signals expected by
the downstream 4-agent scoring pipeline (Income, Repayment, Lifestyle,
Compliance agents).

Signal definitions and detection rules are specified by the Cred-ible
pipeline contract and must not be renamed.
"""

from dataclasses import dataclass, field
import re

import numpy as np
import pandas as pd

from .base import ParsedTransaction


# ---------------------------------------------------------------------------
# Detection keyword lists
# ---------------------------------------------------------------------------

UPI_KEYWORDS = ("upi/", "upi-", "phonepe", "gpay", "paytm", "bhim")

UTILITY_KEYWORDS = (
    "bescom",
    "bwssb",
    "mseb",
    "tata power",
    "adani elec",
    "cesc",
    "torrent",
    "tneb",
    "wbsedcl",
    "jio",
    "airtel",
    " vi ",
    "bsnl",
    "mahanagar gas",
    "igl",
    "mgl",
)

MOBILE_RECHARGE_KEYWORDS = (
    "recharge",
    "topup",
    "top-up",
    "prepaid",
    "jio",
    "airtel",
    "vi",
    "bsnl",
)

INTERNAL_TRANSFER_KEYWORDS = (
    "self transfer",
    "own account",
    "neft to self",
)


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DerivedSignalResult:
    signals: dict[str, int | float]
    statement_months: int
    confidence_score: float
    low_history_warning: bool
    income_undetectable: bool
    upi_inactive: bool
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _normalize_narration(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def _extract_merchant(narration: str) -> str:
    """
    Best-effort merchant name extraction from UPI / NEFT narrations.
    UPI narrations typically look like: UPI/MERCHANT NAME/TXN-ID/...
    """
    cleaned = re.sub(r"[^a-z0-9/\- ]+", " ", narration.lower())
    for separator in ("/", "-"):
        parts = [part.strip() for part in cleaned.split(separator) if part.strip()]
        if len(parts) >= 2:
            return parts[-1][:40]
    tokens = [token for token in cleaned.split() if token not in {"upi", "to", "from", "by"}]
    if not tokens:
        return "unknown"
    return " ".join(tokens[:2])[:40]


def _is_upi(narration: str) -> bool:
    lowered = narration.lower()
    return any(keyword in lowered for keyword in UPI_KEYWORDS)


def _is_internal_transfer(narration: str, borrower_name: str) -> bool:
    """
    Identify internal (self) transfers that should be excluded from income.

    Rules:
      - narration contains "self transfer", "own account", "neft to self"
      - narration contains the borrower's full name (at least 2 tokens with
        length > 2 must all appear) — a single first name is too ambiguous.
    """
    lowered = narration.lower()
    if any(keyword in lowered for keyword in INTERNAL_TRANSFER_KEYWORDS):
        return True
    # Same-name payee detection: require at least 2 significant name tokens
    # to avoid false positives (e.g. "Raju" matching "UPI/RAJU-VENDOR/...")
    name_tokens = [
        token for token in re.split(r"[\s\-]+", borrower_name.lower())
        if len(token) > 2
    ]
    if len(name_tokens) >= 2 and all(token in lowered for token in name_tokens[:2]):
        return True
    return False


def _is_utility(narration: str, amount: int) -> bool:
    """Utility payment: vendor keyword match AND amount between ₹200–₹15,000."""
    lowered = narration.lower()
    if amount < 200 or amount > 15_000:
        return False
    return any(keyword in lowered for keyword in UTILITY_KEYWORDS)


def _utility_timeliness_score(day_of_month: int) -> float:
    """
    On-time scoring for utility payments.
      - Paid on/before 15th → 1.0 (on-time)
      - Paid after 20th     → 0.0 (late)
      - Paid 16th–20th      → 0.5 (neutral)
    """
    if day_of_month <= 15:
        return 1.0
    if day_of_month > 20:
        return 0.0
    return 0.5


def _is_mobile_recharge(narration: str, amount: int) -> bool:
    lowered = narration.lower()
    if amount <= 0 or amount > 3_500:
        return False
    return any(keyword in lowered for keyword in MOBILE_RECHARGE_KEYWORDS)


def _to_frame(transactions: list[ParsedTransaction]) -> pd.DataFrame:
    """Convert parsed transactions to a working DataFrame with derived columns."""
    rows = [
        {
            "date": transaction.date,
            "narration": _normalize_narration(transaction.narration),
            "debit": int(transaction.debit),
            "credit": int(transaction.credit),
            "balance": transaction.balance,
        }
        for transaction in transactions
    ]
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame

    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame = frame.dropna(subset=["date"])
    frame["month"] = frame["date"].dt.to_period("M").astype(str)
    frame["txn_amount_abs"] = frame["debit"] + frame["credit"]
    frame["is_upi"] = frame["narration"].apply(_is_upi)
    frame["merchant"] = frame["narration"].apply(_extract_merchant)
    return frame.sort_values("date")


# ---------------------------------------------------------------------------
# Regularity & trend helpers
# ---------------------------------------------------------------------------

def _monthly_credit_regularity(monthly_credits: pd.Series) -> float:
    """
    regularity_score = 1 - (std_dev / mean), clipped to [0, 1].
    Measures how consistent monthly credit amounts are.
    """
    if monthly_credits.empty:
        return 0.0
    mean_credits = float(monthly_credits.mean())
    if mean_credits <= 0:
        return 0.0
    std_credits = float(monthly_credits.std(ddof=0))
    return _clip(1.0 - (std_credits / mean_credits), 0.0, 1.0)


def _monthly_trend_pct(monthly_values: pd.Series) -> float:
    """
    % change in transaction volume: avg of first 3 months vs. last 3 months.
    Clipped to [-100, +300] to avoid extreme outliers.
    """
    if monthly_values.empty:
        return 0.0
    window = min(3, len(monthly_values))
    first_avg = float(monthly_values.head(window).mean())
    last_avg = float(monthly_values.tail(window).mean())
    if first_avg <= 0:
        return 100.0 if last_avg > 0 else 0.0
    return _clip(((last_avg - first_avg) / first_avg) * 100.0, -100.0, 300.0)


def _estimated_fixed_emi(debit_rows: pd.DataFrame) -> float:
    """
    Detect likely EMI payments:
      - Same approximate amount (±5%) recurring on the same date (±3 days)
        each month, with amount > ₹1,000.
      - Must appear in at least 3 distinct months to count as recurring.

    Returns total monthly EMI estimate (sum of median amounts per EMI cluster).
    """
    if debit_rows.empty:
        return 0.0

    eligible = debit_rows[debit_rows["debit"] > 1_000].copy()
    if eligible.empty:
        return 0.0

    eligible["day"] = eligible["date"].dt.day
    eligible["month_period"] = eligible["date"].dt.to_period("M")

    clusters: list[dict] = []

    for _, row in eligible.iterrows():
        amount = float(row["debit"])
        day = int(row["day"])
        month_period = row["month_period"]
        assigned = False

        for cluster in clusters:
            ref_amount = float(cluster["amount"])
            ref_day = int(cluster["day"])
            if (
                abs(amount - ref_amount) <= (ref_amount * 0.05)
                and abs(day - ref_day) <= 3
            ):
                cluster["amounts"].append(amount)
                cluster["months"].add(month_period)
                assigned = True
                break

        if not assigned:
            clusters.append({
                "amount": amount,
                "day": day,
                "amounts": [amount],
                "months": {month_period},
            })

    # Only count clusters that recur in >= 3 distinct months
    recurring = [c for c in clusters if len(c["months"]) >= 3]
    if not recurring:
        return 0.0

    return float(sum(np.median(c["amounts"]) for c in recurring))


# ---------------------------------------------------------------------------
# Main signal derivation entry point
# ---------------------------------------------------------------------------

def derive_signals(
    transactions: list[ParsedTransaction],
    *,
    borrower_name: str,
) -> DerivedSignalResult:
    """
    Compute all 14 derived signals from a list of parsed transactions.

    This function is the single bridge between raw transaction data and the
    4-agent scoring pipeline.  The returned signal dict keys are fixed by
    pipeline contract and must not be renamed.
    """
    frame = _to_frame(transactions)
    if frame.empty:
        raise ValueError("No valid transaction rows were available for signal derivation.")

    # --- Month index covering the full statement period (incl. gaps) -------
    all_months = pd.period_range(
        frame["date"].min().to_period("M"),
        frame["date"].max().to_period("M"),
        freq="M",
    )
    month_labels = [str(m) for m in all_months]
    statement_months = len(month_labels)

    # --- Monthly aggregates -------------------------------------------------
    monthly = frame.groupby("month", as_index=True).agg(
        monthly_credits=("credit", "sum"),
        monthly_debits=("debit", "sum"),
        monthly_txn_count=("date", "size"),
    )
    monthly = monthly.reindex(month_labels, fill_value=0)

    # -----------------------------------------------------------------------
    # Signal 1 & 2: UPI transaction count and average value
    # -----------------------------------------------------------------------
    upi_rows = frame[frame["is_upi"]]
    upi_monthly_txn_count = int(round(len(upi_rows) / max(statement_months, 1)))
    upi_avg_txn_value = (
        int(round(float(upi_rows["txn_amount_abs"].mean())))
        if not upi_rows.empty else 0
    )

    # -----------------------------------------------------------------------
    # Signal 3: Merchant diversity (unique merchants / total txns, 0–1)
    # -----------------------------------------------------------------------
    merchant_diversity = _clip(
        frame["merchant"].nunique() / max(len(frame), 1),
        0.0,
        1.0,
    )

    # -----------------------------------------------------------------------
    # Signal 4: Regularity score (consistency of monthly credits)
    # -----------------------------------------------------------------------
    regularity_score = _monthly_credit_regularity(monthly["monthly_credits"])

    # -----------------------------------------------------------------------
    # Signal 5 & 6: Monthly income (excluding self-transfers) & stability
    # -----------------------------------------------------------------------
    internal_mask = frame["narration"].apply(
        lambda text: _is_internal_transfer(text, borrower_name)
    )
    income_rows = frame[(frame["credit"] > 0) & (~internal_mask)]
    monthly_income_series = (
        income_rows.groupby("month")["credit"]
        .sum()
        .reindex(month_labels, fill_value=0)
    )
    monthly_income_inr = int(round(float(monthly_income_series.mean())))
    income_stability_score = _monthly_credit_regularity(monthly_income_series)

    income_undetectable = bool(frame["credit"].sum() == 0 or monthly_income_inr <= 0)
    if income_undetectable:
        monthly_income_inr = 0
        income_stability_score = 0.0

    # -----------------------------------------------------------------------
    # Signal 7: Savings rate %
    # -----------------------------------------------------------------------
    credit_nonzero = monthly["monthly_credits"] > 0
    if credit_nonzero.any():
        savings_values = (
            (
                monthly.loc[credit_nonzero, "monthly_credits"]
                - monthly.loc[credit_nonzero, "monthly_debits"]
            )
            / monthly.loc[credit_nonzero, "monthly_credits"]
        ) * 100.0
        savings_rate_pct = float(savings_values.mean())
    else:
        savings_rate_pct = 0.0

    # -----------------------------------------------------------------------
    # Signal 8: Average closing balance (last 3 months)
    # -----------------------------------------------------------------------
    if frame["balance"].notna().any():
        balance_monthly = (
            frame.dropna(subset=["balance"])
            .sort_values("date")
            .groupby("month")["balance"]
            .last()
            .reindex(month_labels)
            .ffill()
            .fillna(0)
        )
    else:
        # No balance column — estimate from cumulative net flow
        running_balance = (monthly["monthly_credits"] - monthly["monthly_debits"]).cumsum()
        balance_monthly = running_balance

    bank_balance_avg_3m = int(round(
        float(balance_monthly.tail(min(3, len(balance_monthly))).mean())
    ))

    # -----------------------------------------------------------------------
    # Signal 9: Debt-to-income ratio (EMI / income)
    # -----------------------------------------------------------------------
    emi_estimate = _estimated_fixed_emi(frame[frame["debit"] > 0].copy())
    debt_to_income_ratio = (
        0.0 if monthly_income_inr <= 0
        else float(emi_estimate / monthly_income_inr)
    )

    # -----------------------------------------------------------------------
    # Signal 10: Utility bill on-time %
    # -----------------------------------------------------------------------
    utility_rows = frame[
        frame.apply(
            lambda row: _is_utility(str(row["narration"]), int(row["txn_amount_abs"])),
            axis=1,
        )
    ]
    if utility_rows.empty:
        utility_bill_ontime_pct = 0.0
    else:
        utility_bill_ontime_pct = float(
            utility_rows["date"].dt.day.apply(_utility_timeliness_score).mean() * 100.0
        )

    # -----------------------------------------------------------------------
    # Signal 11 & 12: Mobile recharge frequency and consistency
    # -----------------------------------------------------------------------
    recharge_rows = frame[
        frame.apply(
            lambda row: _is_mobile_recharge(str(row["narration"]), int(row["txn_amount_abs"])),
            axis=1,
        )
    ]
    mobile_recharge_freq = float(len(recharge_rows) / max(statement_months, 1))

    if len(recharge_rows) >= 2:
        intervals = (
            recharge_rows.sort_values("date")["date"]
            .diff()
            .dt.days
            .dropna()
            .astype(float)
        )
        mean_interval = float(intervals.mean()) if not intervals.empty else 0.0
        std_interval = float(intervals.std(ddof=0)) if not intervals.empty else 0.0
        recharge_consistency_score = (
            _clip(1.0 - (std_interval / max(mean_interval, 1.0)), 0.0, 1.0)
            if mean_interval > 0 else 0.0
        )
    elif len(recharge_rows) == 1:
        recharge_consistency_score = 0.5
    else:
        recharge_consistency_score = 0.0

    # -----------------------------------------------------------------------
    # Signal 13: Months of history
    # (already computed as statement_months)
    # -----------------------------------------------------------------------

    # -----------------------------------------------------------------------
    # Signal 14: Monthly volume trend %
    # -----------------------------------------------------------------------
    monthly_volume_trend_pct = _monthly_trend_pct(monthly["monthly_txn_count"])

    # -----------------------------------------------------------------------
    # Flags & confidence scoring
    # -----------------------------------------------------------------------
    upi_inactive = upi_rows.empty

    confidence = 0.85
    warnings: list[str] = []
    low_history_warning = statement_months < 3

    if low_history_warning:
        confidence = min(confidence, 0.45)
        warnings.append("Statement history is shorter than 3 months.")
    elif statement_months < 6:
        confidence -= 0.10

    if frame["balance"].notna().sum() == 0:
        confidence -= 0.10
        warnings.append("Balance column was missing; balance trend was estimated from net flow.")
    if income_undetectable:
        confidence -= 0.20
        warnings.append("Income could not be inferred from credit transactions.")
    if upi_inactive:
        confidence -= 0.15
        warnings.append("No UPI activity found in the uploaded statement.")
    if len(frame) < 20:
        confidence -= 0.10

    confidence = _clip(confidence, 0.10, 0.99)
    if low_history_warning:
        confidence = min(confidence, 0.49)

    # -----------------------------------------------------------------------
    # Assemble result (field names are fixed by pipeline contract)
    # -----------------------------------------------------------------------
    signals = {
        "upi_monthly_txn_count": int(upi_monthly_txn_count),
        "upi_avg_txn_value": int(upi_avg_txn_value),
        "merchant_diversity_score": round(float(merchant_diversity), 4),
        "regularity_score": round(float(regularity_score), 4),
        "monthly_income_inr": int(monthly_income_inr),
        "income_stability_score": round(float(income_stability_score), 4),
        "savings_rate_pct": round(float(savings_rate_pct), 2),
        "bank_balance_avg_3m": int(bank_balance_avg_3m),
        "debt_to_income_ratio": round(float(debt_to_income_ratio), 4),
        "utility_bill_ontime_pct": round(float(utility_bill_ontime_pct), 2),
        "mobile_recharge_freq": round(float(mobile_recharge_freq), 4),
        "recharge_consistency_score": round(float(recharge_consistency_score), 4),
        "months_of_history": int(statement_months),
        "monthly_volume_trend_pct": round(float(monthly_volume_trend_pct), 2),
    }

    return DerivedSignalResult(
        signals=signals,
        statement_months=statement_months,
        confidence_score=round(float(confidence), 4),
        low_history_warning=low_history_warning,
        income_undetectable=income_undetectable,
        upi_inactive=upi_inactive,
        warnings=warnings,
    )
