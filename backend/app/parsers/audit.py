from __future__ import annotations

from dataclasses import dataclass
from statistics import median
import re

import pandas as pd

from .base import ParsedTransaction

ROUNDING_TOLERANCE_INR = 2

GIG_KEYWORDS = ("swiggy", "zomato", "uber", "ola", "dunzo", "blinkit", "zepto", "payout")
SALARY_KEYWORDS = ("salary", "payroll", "ecs cr")
BUSINESS_KEYWORDS = ("gst", "invoice", "trade", "settlement", "client")
UTILITY_PROVIDER_MAP = {
    "bescom": ("electricity", "BESCOM"),
    "mseb": ("electricity", "MSEB"),
    "tata power": ("electricity", "TATA POWER"),
    "adani elec": ("electricity", "ADANI ELEC"),
    "cesc": ("electricity", "CESC"),
    "torrent": ("electricity", "TORRENT"),
    "tneb": ("electricity", "TNEB"),
    "wbsedcl": ("electricity", "WBSEDCL"),
    "bwssb": ("water", "BWSSB"),
    "water": ("water", "WATER"),
    "jal": ("water", "JAL BOARD"),
    "igl": ("gas", "IGL"),
    "mgl": ("gas", "MGL"),
    "mahanagar gas": ("gas", "MAHANAGAR GAS"),
    "airtel xstream": ("broadband", "AIRTEL XSTREAM"),
    "jiofiber": ("broadband", "JIOFIBER"),
    "act fibernet": ("broadband", "ACT FIBERNET"),
    "hathway": ("broadband", "HATHWAY"),
}
MOBILE_PROVIDER_MAP = {
    "jio": "Jio",
    "airtel": "Airtel",
    " vi ": "Vi",
    "vi ": "Vi",
    "vi/": "Vi",
    "bsnl": "BSNL",
}
ESSENTIAL_KEYWORDS = (
    "d-mart",
    "dmart",
    "kirana",
    "fruit",
    "grocery",
    "fuel",
    "petrol",
    "diesel",
    "pharma",
    "medplus",
    "medical",
)
FOOD_KEYWORDS = ("cafe", "restaurant", "swiggy", "zomato", "eat", "food")
RENT_KEYWORDS = ("rent", "housing", "nobroker", "magicbricks", "landlord")
EMI_KEYWORDS = ("emi", "loan", "nach", "ecs dr", "bajaj", "hdfc ergo", "finance")
BNPL_KEYWORDS = ("lazypay", "zestmoney", "simpl", "postpe", "slice")


@dataclass(frozen=True)
class IncomeAudit:
    income_type: str
    raw_monthly_avg: float
    corrected_monthly_avg: float
    regularity: str
    trend: str
    raw_score: int
    corrected_score: int
    confidence: str
    reasoning: str


@dataclass(frozen=True)
class RepaymentAudit:
    bills_found: list[str]
    emis_found: bool
    rent_found: bool
    score: int
    confidence: str
    confirmed_payments_made: int
    expected_payments: int
    reasoning: str


@dataclass(frozen=True)
class LifestyleAudit:
    essential_ratio: float
    multiple_sims: bool
    score: int
    reasoning: str


@dataclass(frozen=True)
class StatementAuditResult:
    score: int
    flags: list[str]
    missing_months: list[str]
    parallel_balance_tracks: bool
    balance_track_ranges: list[str]
    anomalous_income_months: list[str]
    raw_monthly_income_avg: float
    corrected_monthly_income_avg: float
    rent_payments_found: bool
    utility_consistency: str
    utility_providers: list[str]
    months_without_utility_payments: list[str]
    income: IncomeAudit
    repayment: RepaymentAudit
    lifestyle: LifestyleAudit


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def _to_frame(transactions: list[ParsedTransaction]) -> pd.DataFrame:
    rows = [
        {
            "date": pd.to_datetime(tx.date, errors="coerce"),
            "narration": _normalize(tx.narration),
            "debit": int(tx.debit),
            "credit": int(tx.credit),
            "balance": None if tx.balance is None else int(tx.balance),
        }
        for tx in transactions
    ]
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    frame = frame.dropna(subset=["date"]).sort_values("date")
    frame["month"] = frame["date"].dt.to_period("M")
    return frame


def _confidence_label(value: float) -> str:
    if value >= 0.8:
        return "HIGH"
    if value >= 0.55:
        return "MEDIUM"
    return "LOW"


def _risk_level_from_score(score: int) -> str:
    if score >= 760:
        return "LOW"
    if score >= 620:
        return "MEDIUM"
    return "HIGH"


def _identify_utility_provider(narration: str) -> tuple[str | None, str | None]:
    for keyword, info in UTILITY_PROVIDER_MAP.items():
        if keyword in narration:
            return info
    return (None, None)


def _identify_mobile_provider(narration: str) -> str | None:
    padded = f" {narration} "
    for keyword, provider in MOBILE_PROVIDER_MAP.items():
        if keyword in padded:
            return provider
    return None


def _month_label(period: pd.Period) -> str:
    return period.strftime("%Y-%m")


def _balance_track_ranges(balances: list[int]) -> list[str]:
    if len(balances) < 4:
        if not balances:
            return []
        return [f"Track A: ₹{min(balances):,}–₹{max(balances):,}"]

    ordered = sorted(balances)
    gaps = [ordered[index + 1] - ordered[index] for index in range(len(ordered) - 1)]
    split_index = max(range(len(gaps)), key=gaps.__getitem__)
    left = ordered[: split_index + 1]
    right = ordered[split_index + 1 :]
    if not left or not right or gaps[split_index] < 5_000:
        midpoint = len(ordered) // 2
        left = ordered[:midpoint]
        right = ordered[midpoint:]
    if not left or not right:
        return [f"Track A: ₹{min(ordered):,}–₹{max(ordered):,}"]
    return [
        f"Track A: ₹{min(left):,}–₹{max(left):,}",
        f"Track B: ₹{min(right):,}–₹{max(right):,}",
    ]


def _income_type_from_rows(income_rows: pd.DataFrame) -> str:
    if income_rows.empty:
        return "unclear"
    gig_hits = income_rows["narration"].str.contains("|".join(map(re.escape, GIG_KEYWORDS)), regex=True).sum()
    salary_hits = income_rows["narration"].str.contains("|".join(map(re.escape, SALARY_KEYWORDS)), regex=True).sum()
    business_hits = income_rows["narration"].str.contains("|".join(map(re.escape, BUSINESS_KEYWORDS)), regex=True).sum()
    nonzero = [(gig_hits, "gig"), (salary_hits, "salary"), (business_hits, "business")]
    nonzero = [item for item in nonzero if item[0] > 0]
    if len(nonzero) >= 2:
        return "mixed"
    if nonzero:
        return nonzero[0][1]
    return "unclear"


def _income_regularity(income_rows: pd.DataFrame, month_index: list[pd.Period]) -> str:
    if income_rows.empty or not month_index:
        return "LOW"
    active_days = (
        income_rows.assign(day=income_rows["date"].dt.date)
        .groupby("month")["day"]
        .nunique()
        .reindex(month_index, fill_value=0)
    )
    avg_active_days = float(active_days.mean())
    if avg_active_days >= 20:
        return "HIGH"
    if avg_active_days >= 8:
        return "MEDIUM"
    return "LOW"


def _income_trend(monthly_credits: pd.Series) -> str:
    if monthly_credits.empty:
        return "STABLE"
    window = min(2, len(monthly_credits))
    first_avg = float(monthly_credits.head(window).mean())
    last_avg = float(monthly_credits.tail(window).mean())
    if first_avg <= 0:
        return "IMPROVING" if last_avg > 0 else "STABLE"
    delta = ((last_avg - first_avg) / first_avg) * 100.0
    if delta > 10:
        return "IMPROVING"
    if delta < -10:
        return "DECLINING"
    return "STABLE"


def _income_score(regularity: str, monthly_avg: float, trend: str, income_days_per_month: float) -> int:
    base = 30
    if regularity == "HIGH":
        base = 62
    elif regularity == "MEDIUM":
        base = 48
    elif regularity == "LOW":
        base = 32

    if income_days_per_month > 20 and base < 40:
        base = 40

    if monthly_avg > 30_000:
        base += 10
    elif 20_000 <= monthly_avg <= 30_000:
        base += 5
    elif monthly_avg < 15_000:
        base -= 10

    if trend == "IMPROVING":
        base += 8
    elif trend == "DECLINING":
        base -= 8

    return max(0, min(100, int(round(base))))


def _loan_range_inr(credit_score: int) -> dict[str, int]:
    if credit_score < 500:
        return {"min": 20_000, "max": 50_000}
    if credit_score < 650:
        return {"min": 50_000, "max": 150_000}
    if credit_score < 750:
        return {"min": 150_000, "max": 300_000}
    return {"min": 300_000, "max": 600_000}


def audit_statement_transactions(transactions: list[ParsedTransaction], borrower_name: str) -> StatementAuditResult:
    frame = _to_frame(transactions)
    if frame.empty:
        raise ValueError("No parsed transactions available for statement audit.")

    flags: list[str] = []
    months = pd.period_range(frame["month"].min(), frame["month"].max(), freq="M")
    month_labels = [_month_label(period) for period in months]
    monthly_credit = frame.groupby("month")["credit"].sum().reindex(months, fill_value=0)
    monthly_debit = frame.groupby("month")["debit"].sum().reindex(months, fill_value=0)
    monthly_counts = frame.groupby("month").size().reindex(months, fill_value=0)
    missing_months = [label for label, count in zip(month_labels, monthly_counts.tolist()) if count == 0]
    if missing_months:
        flags.append(f"WARNING — MISSING MONTH GAP. Missing months: {', '.join(missing_months)}")

    balance_checked = 0
    balance_failed = 0
    failed_balances: list[int] = []
    previous_balance: int | None = None
    for _, row in frame.iterrows():
        current_balance = row["balance"]
        if previous_balance is None or current_balance is None:
            previous_balance = current_balance if current_balance is not None else previous_balance
            continue
        balance_checked += 1
        expected = previous_balance + int(row["credit"]) - int(row["debit"])
        if abs(expected - int(current_balance)) > ROUNDING_TOLERANCE_INR:
            balance_failed += 1
            failed_balances.append(int(current_balance))
        previous_balance = int(current_balance)

    parallel_balance_tracks = balance_checked > 0 and (balance_failed / balance_checked) > 0.05
    balance_track_ranges = _balance_track_ranges(failed_balances or [int(value) for value in frame["balance"].dropna().tolist()])
    if parallel_balance_tracks:
        flags.append(
            "CRITICAL — PARALLEL BALANCE TRACKS DETECTED. "
            + (" ".join(balance_track_ranges) if balance_track_ranges else "")
        )

    credit_values = [float(value) for value in monthly_credit.tolist() if value > 0]
    median_credit = float(median(credit_values)) if credit_values else 0.0
    anomalous_income_months = [
        _month_label(period)
        for period, value in monthly_credit.items()
        if median_credit > 0 and float(value) > (1.8 * median_credit)
    ]
    if anomalous_income_months:
        flags.append(
            "WARNING — ANOMALOUS INCOME SPIKE. Months: " + ", ".join(anomalous_income_months)
        )

    raw_monthly_income_avg = float(monthly_credit.mean())
    corrected_series = monthly_credit.drop(labels=[pd.Period(month) for month in anomalous_income_months], errors="ignore")
    corrected_monthly_income_avg = float(corrected_series.mean()) if not corrected_series.empty else raw_monthly_income_avg

    debit_rows = frame[frame["debit"] > 0].copy()
    debit_rows["provider_category"] = debit_rows["narration"].apply(lambda narration: _identify_utility_provider(narration)[0])
    debit_rows["provider_name"] = debit_rows["narration"].apply(lambda narration: _identify_utility_provider(narration)[1])
    utility_rows = debit_rows[debit_rows["provider_name"].notna()].copy()
    utility_providers = sorted({str(value) for value in utility_rows["provider_name"].dropna().tolist()})
    utility_months = sorted(set(utility_rows["month"].tolist()))
    months_without_utility_payments = [_month_label(period) for period in months if period not in utility_months]
    for month in months_without_utility_payments:
        flags.append(f"WARNING — No utility payment detected in {month}")

    board_providers = {
        str(name)
        for name in utility_rows[utility_rows["provider_category"].isin(["electricity", "water"])][
            "provider_name"
        ].dropna().tolist()
    }
    utility_consistency = "inconsistent" if len(board_providers) > 2 else "consistent"
    if utility_consistency == "inconsistent":
        flags.append(
            "NOTICE — MULTIPLE SERVICE PROVIDERS DETECTED. Providers: " + ", ".join(sorted(board_providers))
        )

    direct_rent_rows = debit_rows[
        debit_rows["narration"].str.contains("|".join(map(re.escape, RENT_KEYWORDS)), regex=True)
    ]
    rent_payments_found = not direct_rent_rows.empty
    if not rent_payments_found:
        flags.append(
            "NOTICE — NO RENT PAYMENTS DETECTED. Possible cash rent, second account, or rent-free living."
        )

    debit_rows["mobile_provider"] = debit_rows["narration"].apply(_identify_mobile_provider)
    mobile_rows = debit_rows[debit_rows["mobile_provider"].notna()].copy()
    providers_by_month = mobile_rows.groupby("month")["mobile_provider"].nunique() if not mobile_rows.empty else pd.Series(dtype=int)
    multiple_sims = bool((providers_by_month > 1).any())
    if multiple_sims:
        flags.append("NOTICE — Multiple mobile providers detected in at least one month.")

    essentials_mask = debit_rows["narration"].str.contains("|".join(map(re.escape, ESSENTIAL_KEYWORDS)), regex=True)
    food_mask = debit_rows["narration"].str.contains("|".join(map(re.escape, FOOD_KEYWORDS)), regex=True)
    discretionary_mask = ~(essentials_mask | food_mask | debit_rows["provider_name"].notna() | debit_rows["mobile_provider"].notna())
    total_spend = float(debit_rows["debit"].sum()) or 1.0
    essentials_spend = float(debit_rows.loc[essentials_mask | debit_rows["provider_name"].notna(), "debit"].sum())
    discretionary_spend = float(debit_rows.loc[discretionary_mask, "debit"].sum())
    essential_ratio = max(0.0, min(1.0, essentials_spend / total_spend))

    pharmacy_mask = debit_rows["narration"].str.contains("pharma|medplus|medical", regex=True)
    monthly_pharmacy = debit_rows[pharmacy_mask].groupby("month")["debit"].sum().reindex(months, fill_value=0)
    if corrected_monthly_income_avg > 0 and (monthly_pharmacy > (0.10 * corrected_monthly_income_avg)).any():
        flags.append("NOTICE — Pharmacy spend exceeded 10% of monthly income in at least one month.")

    income_rows = frame[frame["credit"] > 0].copy()
    income_type = _income_type_from_rows(income_rows)
    regularity = _income_regularity(income_rows, list(months))
    trend = _income_trend(corrected_series if not corrected_series.empty else monthly_credit)
    income_days = (
        income_rows.assign(day=income_rows["date"].dt.date)
        .groupby("month")["day"]
        .nunique()
        .reindex(months, fill_value=0)
    )
    avg_income_days = float(income_days.mean()) if not income_days.empty else 0.0
    raw_score = _income_score(regularity, raw_monthly_income_avg, trend, avg_income_days)
    corrected_score = _income_score(regularity, corrected_monthly_income_avg, trend, avg_income_days)
    clean_months = len(months) - len(missing_months)
    income_confidence = "LOW" if clean_months < 3 or missing_months else "HIGH" if clean_months > 4 else "MEDIUM"
    income_reasoning = (
        f"Detected {income_type} income patterns with {regularity.lower()} payout regularity. "
        f"Raw average monthly credits were ₹{raw_monthly_income_avg:,.0f} and corrected average after anomaly filtering is "
        f"₹{corrected_monthly_income_avg:,.0f}. Trend is {trend.lower()}."
    )

    bill_names = sorted(set(utility_providers))
    emis_found = bool(
        debit_rows["narration"].str.contains("|".join(map(re.escape, EMI_KEYWORDS + BNPL_KEYWORDS)), regex=True).any()
    )
    utility_expected = len(months) if utility_providers else 0
    rent_expected = len(months) if rent_payments_found else 0
    emi_months = (
        debit_rows[
            debit_rows["narration"].str.contains("|".join(map(re.escape, EMI_KEYWORDS + BNPL_KEYWORDS)), regex=True)
        ]["month"].nunique()
        if emis_found
        else 0
    )
    emi_expected = len(months) if emis_found else 0
    utility_confirmed = len(set(utility_rows["month"].tolist()))
    rent_confirmed = len(set(direct_rent_rows["month"].tolist()))
    confirmed_payments = utility_confirmed + rent_confirmed + int(emi_months)
    expected_payments = utility_expected + rent_expected + emi_expected
    completion_ratio = confirmed_payments / expected_payments if expected_payments else 0.0
    repayment_score = int(round(completion_ratio * 100)) if expected_payments else 0
    if utility_expected and utility_confirmed == utility_expected:
        repayment_score += 20
    repayment_score -= len(months_without_utility_payments) * 8
    if emis_found and emi_expected and emi_months >= max(1, len(months) - 1):
        repayment_score += 15
    repayment_score = max(0, min(100, repayment_score))
    repayment_confidence = _confidence_label(max(0.0, min(1.0, completion_ratio + (0.2 if clean_months >= 4 else 0.0))))
    repayment_reasoning = (
        f"We can confirm {confirmed_payments} out of {expected_payments} expected monthly payments were made. "
        "On-time means the payment appears within the same calendar month; exact due dates cannot be verified from a statement alone."
    )

    lifestyle_score = 50
    if essential_ratio > 0.60:
        lifestyle_score += 15
    if not mobile_rows.empty and mobile_rows["month"].nunique() == len(months):
        lifestyle_score += 5
    if discretionary_spend / total_spend > 0.30:
        lifestyle_score -= 10
    lifestyle_score = max(0, min(100, lifestyle_score))
    lifestyle_reasoning = (
        f"Essentials account for {essential_ratio:.0%} of debit spend. "
        f"Mobile recharge activity is {'present every month' if not mobile_rows.empty and mobile_rows['month'].nunique() == len(months) else 'not visible every month'}, "
        f"and multiple active SIM indicators are {'present' if multiple_sims else 'not present'}."
    )

    data_quality_score = 100
    if parallel_balance_tracks:
        data_quality_score -= 40
    data_quality_score -= len(missing_months) * 10
    if anomalous_income_months:
        data_quality_score -= 15
    if not rent_payments_found:
        data_quality_score -= 5
    if utility_consistency == "inconsistent":
        data_quality_score -= 5
    data_quality_score = max(0, min(100, data_quality_score))

    return StatementAuditResult(
        score=data_quality_score,
        flags=flags,
        missing_months=missing_months,
        parallel_balance_tracks=parallel_balance_tracks,
        balance_track_ranges=balance_track_ranges,
        anomalous_income_months=anomalous_income_months,
        raw_monthly_income_avg=raw_monthly_income_avg,
        corrected_monthly_income_avg=corrected_monthly_income_avg,
        rent_payments_found=rent_payments_found,
        utility_consistency=utility_consistency,
        utility_providers=utility_providers,
        months_without_utility_payments=months_without_utility_payments,
        income=IncomeAudit(
            income_type=income_type,
            raw_monthly_avg=raw_monthly_income_avg,
            corrected_monthly_avg=corrected_monthly_income_avg,
            regularity=regularity,
            trend=trend,
            raw_score=raw_score,
            corrected_score=corrected_score,
            confidence=income_confidence,
            reasoning=income_reasoning,
        ),
        repayment=RepaymentAudit(
            bills_found=bill_names,
            emis_found=emis_found,
            rent_found=rent_payments_found,
            score=repayment_score,
            confidence=repayment_confidence,
            confirmed_payments_made=confirmed_payments,
            expected_payments=expected_payments,
            reasoning=repayment_reasoning,
        ),
        lifestyle=LifestyleAudit(
            essential_ratio=essential_ratio,
            multiple_sims=multiple_sims,
            score=lifestyle_score,
            reasoning=lifestyle_reasoning,
        ),
    )
