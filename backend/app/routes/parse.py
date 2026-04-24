from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
import random

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import ValidationError

from ..parsers import parse_statement_file
from ..parsers.base import ParsedTransaction, ParserError
from ..parsers.signals import derive_signals
from ..schemas.parse import (
    ParsePersonaSet,
    ParsePersonasResponse,
    ParseRequest,
    ParseResponse,
    ParsedSignals,
)


router = APIRouter(prefix="/parse", tags=["statement-parser"])

SUPPORTED_STATEMENT_EXTENSIONS = {".pdf", ".csv"}
PERSONA_HISTORY_MONTHS = 6


@dataclass(frozen=True)
class PersonaProfile:
    borrower_name: str
    employment_type: str
    gst_applicable: bool
    loan_amount_requested: int
    detected_bank: str
    kind: str


@dataclass(frozen=True)
class TxSeedRow:
    tx_date: datetime
    narration: str
    debit: int
    credit: int
    balance: int


PERSONA_PROFILES: tuple[PersonaProfile, ...] = (
    PersonaProfile(
        borrower_name="Raju",
        employment_type="self_employed",
        gst_applicable=False,
        loan_amount_requested=120_000,
        detected_bank="sbi",
        kind="raju",
    ),
    PersonaProfile(
        borrower_name="Priya",
        employment_type="freelance",
        gst_applicable=False,
        loan_amount_requested=350_000,
        detected_bank="hdfc",
        kind="priya",
    ),
    PersonaProfile(
        borrower_name="Arjun",
        employment_type="self_employed",
        gst_applicable=False,
        loan_amount_requested=150_000,
        detected_bank="sbi",
        kind="arjun",
    ),
    PersonaProfile(
        borrower_name="Meena",
        employment_type="self_employed",
        gst_applicable=True,
        loan_amount_requested=600_000,
        detected_bank="hdfc",
        kind="meena",
    ),
)

UTILITY_VENDORS = (
    "BESCOM",
    "BWSSB",
    "MSEB",
    "TATA POWER",
    "ADANI ELEC",
    "CESC",
    "TORRENT",
    "TNEB",
    "WBSEDCL",
    "Jio",
    "Airtel",
    "Vi",
    "BSNL",
    "Mahanagar Gas",
    "IGL",
    "MGL",
)
MERCHANTS = (
    "KIRANA MART",
    "FRUIT ZONE",
    "FUEL HUB",
    "MEDPLUS",
    "UDUPI CAFE",
    "LOCAL STORE",
    "GREEN GROCERY",
)


def _field_error(field: str, message: str) -> list[dict[str, str | list[str]]]:
    return [{"loc": ["body", field], "msg": message, "type": "value_error"}]


def _month_start(months_ago: int) -> date:
    now = datetime.utcnow()
    first = date(year=now.year, month=now.month, day=1)
    month_index = first.month - 1 - months_ago
    year = first.year + (month_index // 12)
    month = (month_index % 12) + 1
    return date(year=year, month=month, day=1)


def _append_row(
    rows: list[TxSeedRow],
    tx_date: date,
    narration: str,
    debit: int,
    credit: int,
) -> None:
    previous_balance = rows[-1].balance if rows else 20_000
    balance = max(0, previous_balance + int(credit) - int(debit))
    rows.append(
        TxSeedRow(
            tx_date=datetime(tx_date.year, tx_date.month, tx_date.day),
            narration=narration,
            debit=max(0, int(debit)),
            credit=max(0, int(credit)),
            balance=int(balance),
        )
    )


def _generate_raju(rows: list[TxSeedRow], month_anchor: date, rng: random.Random) -> None:
    for day in range(1, 29):
        tx_date = month_anchor + timedelta(days=day - 1)
        if tx_date.weekday() == 6:
            continue
        _append_row(rows, tx_date, f"UPI/RAJU-VENDOR/{rng.randint(100000, 999999)}", 0, rng.randint(700, 2300))
        if day % 2 == 0:
            _append_row(rows, tx_date, f"UPI/TO/{rng.choice(MERCHANTS)}", rng.randint(150, 900), 0)
    utility_day = rng.randint(6, 14)
    _append_row(
        rows,
        month_anchor + timedelta(days=utility_day - 1),
        f"BILLPAY/{rng.choice(UTILITY_VENDORS)}",
        rng.randint(600, 1500),
        0,
    )


def _generate_priya(rows: list[TxSeedRow], month_anchor: date, rng: random.Random) -> None:
    for _ in range(rng.randint(1, 2)):
        payout_day = rng.randint(4, 22)
        _append_row(
            rows,
            month_anchor + timedelta(days=payout_day - 1),
            "NEFT/CLIENT INVOICE CREDIT",
            0,
            rng.randint(24_000, 50_000),
        )
    for day in range(2, 28, 3):
        _append_row(
            rows,
            month_anchor + timedelta(days=day - 1),
            f"UPI/TO/{rng.choice(MERCHANTS)}",
            rng.randint(350, 2400),
            0,
        )
    utility_day = rng.choice((12, 13, 15, 22, 24))
    _append_row(
        rows,
        month_anchor + timedelta(days=utility_day - 1),
        f"BILLPAY/{rng.choice(UTILITY_VENDORS)}",
        rng.randint(950, 3300),
        0,
    )


def _generate_arjun(rows: list[TxSeedRow], month_anchor: date, rng: random.Random) -> None:
    for day in range(1, 29):
        tx_date = month_anchor + timedelta(days=day - 1)
        source = rng.choice(("SWIGGY", "ZOMATO"))
        _append_row(rows, tx_date, f"UPI/{source} PAYOUT", 0, rng.randint(550, 1800))
        if day % 3 == 0:
            _append_row(rows, tx_date, f"UPI/TO/{rng.choice(MERCHANTS)}", rng.randint(170, 820), 0)
        if day % 7 == 0:
            _append_row(
                rows,
                tx_date,
                f"MOBILE RECHARGE/{rng.choice(('Jio', 'Airtel', 'Vi'))}",
                rng.randint(239, 399),
                0,
            )
    _append_row(
        rows,
        month_anchor + timedelta(days=10),
        f"BILLPAY/{rng.choice(UTILITY_VENDORS)}",
        rng.randint(700, 1850),
        0,
    )


def _generate_meena(rows: list[TxSeedRow], month_anchor: date, rng: random.Random) -> None:
    for day in range(2, 27, 2):
        tx_date = month_anchor + timedelta(days=day - 1)
        _append_row(rows, tx_date, "UPI/BUSINESS SALE CREDIT", 0, rng.randint(1600, 6800))
        if day % 4 == 0:
            _append_row(rows, tx_date, "NEFT/WHOLESALE PAYMENT RECEIVED", 0, rng.randint(9000, 28_000))
    _append_row(rows, month_anchor + timedelta(days=4), "EMI/SME-TERM-LOAN", 12_000, 0)
    _append_row(rows, month_anchor + timedelta(days=18), "EMI/WORKING-CAPITAL-LOAN", 9_000, 0)
    _append_row(
        rows,
        month_anchor + timedelta(days=9),
        f"BILLPAY/{rng.choice(UTILITY_VENDORS)}",
        rng.randint(1200, 4900),
        0,
    )
    _append_row(rows, month_anchor + timedelta(days=15), "GST PAYMENT/RETURN FILING", rng.randint(2200, 8200), 0)


PERSONA_GENERATORS = {
    "raju": _generate_raju,
    "priya": _generate_priya,
    "arjun": _generate_arjun,
    "meena": _generate_meena,
}


def _build_persona_transactions(profile: PersonaProfile) -> list[ParsedTransaction]:
    rng = random.Random(f"credible-{profile.kind}-signals")
    rows: list[TxSeedRow] = []
    generator = PERSONA_GENERATORS[profile.kind]

    for month_offset in reversed(range(PERSONA_HISTORY_MONTHS)):
        generator(rows, _month_start(month_offset), rng)

    rows.sort(key=lambda item: item.tx_date)
    return [
        ParsedTransaction(
            date=row.tx_date,
            narration=row.narration,
            debit=row.debit,
            credit=row.credit,
            balance=row.balance,
        )
        for row in rows
    ]


def _build_persona_response(profile: PersonaProfile) -> ParsePersonaSet:
    derived = derive_signals(
        _build_persona_transactions(profile),
        borrower_name=profile.borrower_name,
    )
    return ParsePersonaSet(
        borrower_name=profile.borrower_name,
        employment_type=profile.employment_type,
        gst_applicable=profile.gst_applicable,
        loan_amount_requested=profile.loan_amount_requested,
        response=ParseResponse(
            parsed_signals=ParsedSignals(**derived.signals),
            detected_bank=profile.detected_bank,
            statement_months=derived.statement_months,
            confidence_score=derived.confidence_score,
            low_history_warning=derived.low_history_warning,
            income_undetectable=derived.income_undetectable,
            upi_inactive=derived.upi_inactive,
            parser_warnings=derived.warnings,
        ),
    )


PERSONA_SIGNAL_SETS = ParsePersonasResponse(
    personas=[_build_persona_response(profile) for profile in PERSONA_PROFILES]
)


@router.post("/statement", response_model=ParseResponse)
async def parse_statement_endpoint(
    file: UploadFile = File(...),
    borrower_name: str = Form(...),
    employment_type: str = Form(...),
    gst_applicable: bool = Form(...),
    loan_amount_requested: int = Form(...),
) -> ParseResponse:
    try:
        request = ParseRequest(
            borrower_name=borrower_name,
            employment_type=employment_type,
            gst_applicable=gst_applicable,
            loan_amount_requested=loan_amount_requested,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    if not file.filename:
        raise HTTPException(
            status_code=422,
            detail=_field_error("file", "Missing statement file name."),
        )

    extension = Path(file.filename).suffix.lower()
    if extension not in SUPPORTED_STATEMENT_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=_field_error(
                "file",
                f"Unsupported format '{extension}'. Upload a PDF or CSV bank statement.",
            ),
        )

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=422,
            detail=_field_error("file", "Uploaded statement file is empty."),
        )

    try:
        parsed = parse_statement_file(
            filename=file.filename,
            content=content,
            borrower_name=request.borrower_name,
        )
    except ParserError as exc:
        raise HTTPException(
            status_code=422,
            detail=_field_error("file", str(exc)),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=_field_error("statement", str(exc)),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=_field_error(
                "file",
                f"Unexpected error during statement parsing: {exc}",
            ),
        ) from exc

    return ParseResponse(
        parsed_signals=ParsedSignals(**parsed.parsed_signals),
        detected_bank=parsed.detected_bank,
        statement_months=parsed.statement_months,
        confidence_score=parsed.confidence_score,
        low_history_warning=parsed.low_history_warning,
        income_undetectable=parsed.income_undetectable,
        upi_inactive=parsed.upi_inactive,
        parser_warnings=parsed.parser_warnings,
    )


@router.get("/personas", response_model=ParsePersonasResponse)
async def parse_personas_endpoint() -> ParsePersonasResponse:
    return PERSONA_SIGNAL_SETS
