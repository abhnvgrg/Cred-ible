from __future__ import annotations

import io

import pandas as pd
import pytest

from app.statement_parser import (
    _clamp,
    _find_column,
    _longest_month_gap,
    _normalize_column_name,
    _prepare_monthly_trend,
    derive_signals_from_statement,
)


def csv_bytes(rows: list[dict], columns: list[str] | None = None) -> bytes:
    frame = pd.DataFrame(rows, columns=columns)
    return frame.to_csv(index=False).encode("utf-8")


def upi_rows(months: int = 12, per_month: int = 20, amount: float = 500.0) -> list[dict]:
    rows = []
    for month in range(months):
        for day in range(per_month):
            rows.append(
                {
                    "transaction_date": f"2025-{(month % 12) + 1:02d}-{(day % 28) + 1:02d}",
                    "amount": amount,
                    "merchant": f"merchant_{day % 7}",
                }
            )
    return rows


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Transaction Date", "transaction_date"),
        ("  AMOUNT  ", "amount"),
        ("Amount (INR)", "amount_inr"),
        ("txn-amount", "txn_amount"),
    ],
)
def test_column_names_are_normalised(raw, expected):
    assert _normalize_column_name(raw) == expected


def test_a_column_is_found_by_any_of_its_aliases():
    columns = ["date", "value", "narration"]

    assert _find_column(columns, "transaction_date", "date") == "date"
    assert _find_column(columns, "amount", "value") == "value"
    assert _find_column(columns, "missing", "absent") is None


@pytest.mark.parametrize(
    "value,lower,upper,expected",
    [(5, 0, 10, 5), (-1, 0, 10, 0), (20, 0, 10, 10), (0.5, 0.0, 1.0, 0.5)],
)
def test_clamping_keeps_values_inside_bounds(value, lower, upper, expected):
    assert _clamp(value, lower, upper) == expected


def test_a_rising_series_gives_a_positive_trend():
    assert _prepare_monthly_trend(pd.Series([100, 120, 140, 160])) > 0


def test_a_falling_series_gives_a_negative_trend():
    assert _prepare_monthly_trend(pd.Series([160, 140, 120, 100])) < 0


def test_a_flat_series_has_no_trend():
    assert _prepare_monthly_trend(pd.Series([100, 100, 100])) == pytest.approx(0.0, abs=1e-6)


def test_a_single_month_cannot_have_a_trend():
    assert _prepare_monthly_trend(pd.Series([100])) == 0.0


def test_an_empty_series_has_no_trend():
    assert _prepare_monthly_trend(pd.Series([], dtype=float)) == 0.0


def test_consecutive_months_have_no_gap():
    dates = pd.to_datetime(["2025-01-05", "2025-02-05", "2025-03-05"])
    assert _longest_month_gap(pd.Series(dates)) == 0


def test_a_missing_month_is_reported_as_a_gap():
    dates = pd.to_datetime(["2025-01-05", "2025-04-05"])
    assert _longest_month_gap(pd.Series(dates)) == 2


def test_the_longest_gap_wins():
    dates = pd.to_datetime(["2025-01-05", "2025-02-05", "2025-08-05", "2025-09-05"])
    assert _longest_month_gap(pd.Series(dates)) == 5


@pytest.mark.parametrize("extension", [".txt", ".pdf", ".exe", ".json", ""])
def test_unsupported_file_types_are_refused(extension):
    with pytest.raises(ValueError, match="Unsupported file type"):
        derive_signals_from_statement("upi", f"statement{extension}", b"anything")


def test_an_empty_file_is_refused():
    with pytest.raises(ValueError, match="empty"):
        derive_signals_from_statement("upi", "statement.csv", b"date,amount\n")


def test_an_unknown_signal_type_is_refused():
    with pytest.raises(ValueError, match="Unsupported signal type"):
        derive_signals_from_statement("astrology", "statement.csv", csv_bytes(upi_rows()))


def test_a_statement_without_the_needed_columns_is_refused():
    payload = csv_bytes([{"unrelated": 1, "columns": 2}])

    with pytest.raises(ValueError):
        derive_signals_from_statement("upi", "statement.csv", payload)


def test_upi_signals_are_derived_from_a_statement():
    result = derive_signals_from_statement("upi", "upi.csv", csv_bytes(upi_rows()))

    assert result.derived_fields["transaction_frequency_per_month"] > 0
    assert result.derived_fields["average_transaction_value_inr"] == pytest.approx(500.0)
    assert 0.0 <= result.derived_fields["merchant_diversity_score"] <= 1.0
    assert 0.0 <= result.derived_fields["regularity_score"] <= 1.0
    assert result.derived_fields["months_of_history"] >= 1


def test_derived_upi_signals_satisfy_their_schema():
    from app.schemas import UPISignal

    result = derive_signals_from_statement("upi", "upi.csv", csv_bytes(upi_rows()))

    UPISignal(**result.derived_fields)


def test_more_merchants_raise_the_diversity_score():
    single = [
        {"transaction_date": f"2025-01-{d:02d}", "amount": 100.0, "merchant": "one"}
        for d in range(1, 26)
    ]
    many = [
        {"transaction_date": f"2025-01-{d:02d}", "amount": 100.0, "merchant": f"m{d}"}
        for d in range(1, 26)
    ]

    low = derive_signals_from_statement("upi", "a.csv", csv_bytes(single))
    high = derive_signals_from_statement("upi", "b.csv", csv_bytes(many))

    assert high.derived_fields["merchant_diversity_score"] > low.derived_fields["merchant_diversity_score"]


def test_column_aliases_are_accepted():
    aliased = [
        {"Date": "2025-01-05", "Value": 250.0, "Narration": "shop"},
        {"Date": "2025-02-05", "Value": 250.0, "Narration": "cafe"},
    ]

    result = derive_signals_from_statement("upi", "aliased.csv", csv_bytes(aliased))

    assert result.derived_fields["average_transaction_value_inr"] == pytest.approx(250.0)


def test_a_latin_1_encoded_file_is_still_read():
    frame = pd.DataFrame(
        [{"transaction_date": "2025-01-05", "amount": 100.0, "merchant": "caf\xe9"}]
    )
    payload = frame.to_csv(index=False).encode("latin-1")

    result = derive_signals_from_statement("upi", "latin.csv", payload)

    assert result.derived_fields["average_transaction_value_inr"] == pytest.approx(100.0)


def test_rows_that_are_entirely_blank_are_dropped():
    rows = upi_rows(months=2, per_month=5)
    with_blanks = rows + [{"transaction_date": None, "amount": None, "merchant": None}]

    result = derive_signals_from_statement("upi", "blank.csv", csv_bytes(with_blanks))

    assert result.derived_fields["transaction_frequency_per_month"] > 0


def test_rent_signals_are_derived():
    rows = [
        {"payment_date": f"2025-{m:02d}-05", "amount": 15000.0, "status": "paid"}
        for m in range(1, 13)
    ]

    result = derive_signals_from_statement("rent", "rent.csv", csv_bytes(rows))

    assert result.derived_fields["rent_amount_inr"] > 0
    assert 0.0 <= result.derived_fields["on_time_payment_ratio"] <= 1.0
    assert result.derived_fields["tenancy_months"] >= 1


def test_utility_signals_are_derived():
    rows = [
        {"bill_date": f"2025-{m:02d}-10", "amount": 1800.0, "status": "paid"}
        for m in range(1, 13)
    ]

    result = derive_signals_from_statement("utilities", "utility.csv", csv_bytes(rows))

    assert result.derived_fields["average_monthly_total_inr"] > 0
    assert result.derived_fields["payment_months_observed"] >= 1


def test_employment_signals_are_derived():
    rows = [
        {"salary_date": f"2025-{m:02d}-01", "amount": 60000.0}
        for m in range(1, 13)
    ]

    result = derive_signals_from_statement("employment", "salary.csv", csv_bytes(rows))

    assert result.derived_fields["monthly_income_inr"] > 0
    assert 0.0 <= result.derived_fields["income_stability_score"] <= 1.0


def test_gst_signals_are_derived():
    rows = [
        {"filing_date": f"2025-{m:02d}-20", "taxable_value": 400000.0, "status": "filed"}
        for m in range(1, 13)
    ]

    result = derive_signals_from_statement("gst", "gst.csv", csv_bytes(rows))

    assert 0.0 <= result.derived_fields["filing_consistency_score"] <= 1.0
    assert result.derived_fields["missed_filings_last_12m"] >= 0


def test_parsing_is_deterministic():
    payload = csv_bytes(upi_rows())

    first = derive_signals_from_statement("upi", "upi.csv", payload)
    second = derive_signals_from_statement("upi", "upi.csv", payload)

    assert first.derived_fields == second.derived_fields


def test_malformed_numbers_do_not_crash_the_parser():
    rows = [
        {"transaction_date": "2025-01-05", "amount": "not-a-number", "merchant": "a"},
        {"transaction_date": "2025-01-06", "amount": 200.0, "merchant": "b"},
        {"transaction_date": "2025-02-06", "amount": 300.0, "merchant": "c"},
    ]

    result = derive_signals_from_statement("upi", "messy.csv", csv_bytes(rows))

    assert result.derived_fields["average_transaction_value_inr"] > 0


def test_an_excel_statement_is_read():
    buffer = io.BytesIO()
    pd.DataFrame(upi_rows(months=3, per_month=5)).to_excel(buffer, index=False)

    result = derive_signals_from_statement("upi", "upi.xlsx", buffer.getvalue())

    assert result.derived_fields["transaction_frequency_per_month"] > 0
