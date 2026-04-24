"""
Synthetic Bank Statement Generator for Cred-ible
=================================================
Produces realistic bank statements in PDF and CSV for 4 test personas:

  Raju  — street vendor, high UPI, irregular ₹18k–35k, no EMIs
  Priya — freelancer, lumpy ₹45k–90k, occasional missed utility
  Arjun — gig worker, daily small credits ₹22k–38k, weekly recharges
  Meena — micro-entrepreneur, mixed UPI+NEFT ₹55k–1.2L, 2 EMIs, GST

Usage:
    python generate_test_statements.py
    → writes 8 files into generated_statements/

Statement format rules:
  - PDF layouts are generated with reportlab using SBI/HDFC-style table headers.
  - CSV exports use actual SBI/HDFC export headers.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
import random

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet


@dataclass(frozen=True)
class TransactionRow:
    tx_date: date
    narration: str
    debit: int
    credit: int
    balance: int


@dataclass(frozen=True)
class PersonaConfig:
    name: str
    statement_format: str
    min_income: int
    max_income: int
    notes: str


PERSONAS = [
    PersonaConfig("raju", "sbi", 18_000, 35_000,
                  "Street vendor, high UPI frequency, no EMIs, consistent utility payments."),
    PersonaConfig("priya", "hdfc", 45_000, 90_000,
                  "Freelancer with lumpy large credits and occasional delayed utility payment."),
    PersonaConfig("arjun", "sbi", 22_000, 38_000,
                  "Gig worker with daily small credits and weekly prepaid mobile recharges."),
    PersonaConfig("meena", "hdfc", 55_000, 120_000,
                  "Micro-entrepreneur with mixed UPI+NEFT credits, GST narrations, and 2 EMIs."),
]

UTILITY_VENDORS = ["BESCOM", "BWSSB", "TATA POWER", "Jio", "Airtel", "Mahanagar Gas", "IGL"]
MERCHANTS = ["KIRANA", "FRUIT MART", "FUEL STATION", "PHARMA", "D-MART", "MEDPLUS", "UDUPI CAFE"]


def _month_anchor(month_offset: int) -> date:
    today = date.today().replace(day=1)
    target = today - timedelta(days=month_offset * 30)
    return target.replace(day=1)


def _fmt(value: int) -> str:
    return f"{value:,.2f}"


def _append(rows: list[TransactionRow], tx_date: date, narration: str, debit: int, credit: int) -> None:
    prev = rows[-1].balance if rows else 15_000
    bal = max(0, prev + credit - debit)
    rows.append(TransactionRow(tx_date=tx_date, narration=narration,
                               debit=max(0, debit), credit=max(0, credit), balance=bal))


# ── Persona generators ────────────────────────────────────────────────────

def _gen_raju(rows: list[TransactionRow], ms: date, rng: random.Random) -> None:
    for day in range(1, 29):
        td = ms + timedelta(days=day - 1)
        if td.weekday() == 6:
            continue
        _append(rows, td, f"UPI/RAJU-VENDOR/{rng.randint(100000,999999)}", 0, rng.randint(600, 2200))
        if day % 2 == 0:
            _append(rows, td, f"UPI/TO/{rng.choice(MERCHANTS)}", rng.randint(120, 850), 0)
    ud = rng.randint(8, 14)
    _append(rows, ms + timedelta(days=ud - 1), f"BILLPAY/{rng.choice(UTILITY_VENDORS)}", rng.randint(550, 1400), 0)


def _gen_priya(rows: list[TransactionRow], ms: date, rng: random.Random) -> None:
    for _ in range(rng.randint(1, 2)):
        pd_ = rng.randint(3, 22)
        _append(rows, ms + timedelta(days=pd_ - 1), "NEFT/CLIENT INVOICE CREDIT", 0, rng.randint(22_000, 48_000))
    for day in range(2, 27, 3):
        _append(rows, ms + timedelta(days=day - 1), f"UPI/TO/{rng.choice(MERCHANTS)}", rng.randint(350, 2200), 0)
    ud = rng.choice([12, 14, 23, 24])
    _append(rows, ms + timedelta(days=ud - 1), f"BILLPAY/{rng.choice(UTILITY_VENDORS)}", rng.randint(900, 3200), 0)


def _gen_arjun(rows: list[TransactionRow], ms: date, rng: random.Random) -> None:
    for day in range(1, 29):
        td = ms + timedelta(days=day - 1)
        src = rng.choice(["SWIGGY", "ZOMATO"])
        _append(rows, td, f"UPI/{src} PAYOUT", 0, rng.randint(500, 1700))
        if day % 3 == 0:
            _append(rows, td, f"UPI/TO/{rng.choice(MERCHANTS)}", rng.randint(150, 780), 0)
        if day % 7 == 0:
            _append(rows, td, f"MOBILE RECHARGE/{rng.choice(['Jio','Airtel','Vi'])}", rng.randint(239, 399), 0)
    _append(rows, ms + timedelta(days=11), f"BILLPAY/{rng.choice(UTILITY_VENDORS)}", rng.randint(650, 1800), 0)


def _gen_meena(rows: list[TransactionRow], ms: date, rng: random.Random) -> None:
    for day in range(2, 26, 2):
        td = ms + timedelta(days=day - 1)
        _append(rows, td, "UPI/BUSINESS SALE CREDIT", 0, rng.randint(1500, 6500))
        if day % 4 == 0:
            _append(rows, td, "NEFT/WHOLESALE PAYMENT RECEIVED", 0, rng.randint(8000, 26_000))
    _append(rows, ms + timedelta(days=4), "EMI/SME-TERM-LOAN", 12_000, 0)
    _append(rows, ms + timedelta(days=18), "EMI/WORKING-CAPITAL-LOAN", 9_000, 0)
    _append(rows, ms + timedelta(days=9), f"BILLPAY/{rng.choice(UTILITY_VENDORS)}", rng.randint(1200, 4800), 0)
    _append(rows, ms + timedelta(days=15), "GST PAYMENT/RETURN FILING", rng.randint(2000, 8000), 0)


_GENERATORS = {"raju": _gen_raju, "priya": _gen_priya, "arjun": _gen_arjun, "meena": _gen_meena}


def generate_transactions(persona: PersonaConfig, months: int = 6) -> list[TransactionRow]:
    rng = random.Random(f"credible-{persona.name}-seed")
    rows: list[TransactionRow] = []
    gen = _GENERATORS[persona.name]
    for offset in reversed(range(months)):
        gen(rows, _month_anchor(offset), rng)
    rows.sort(key=lambda r: r.tx_date)
    return rows


# ── Bank-specific DataFrame formatters ────────────────────────────────────

def to_sbi_frame(rows: list[TransactionRow]) -> pd.DataFrame:
    return pd.DataFrame({
        "Txn Date": [r.tx_date.strftime("%d/%m/%Y") for r in rows],
        "Value Date": [r.tx_date.strftime("%d/%m/%Y") for r in rows],
        "Description": [r.narration for r in rows],
        "Ref No./Cheque No.": [f"REF{i:06d}" for i, _ in enumerate(rows, 1)],
        "Debit": [_fmt(r.debit) if r.debit > 0 else "" for r in rows],
        "Credit": [_fmt(r.credit) if r.credit > 0 else "" for r in rows],
        "Balance": [_fmt(r.balance) for r in rows],
    })


def to_hdfc_frame(rows: list[TransactionRow]) -> pd.DataFrame:
    return pd.DataFrame({
        "Date": [r.tx_date.strftime("%d-%m-%Y") for r in rows],
        "Narration": [r.narration for r in rows],
        "Chq./Ref.No.": [f"CHQ{i:06d}" for i, _ in enumerate(rows, 1)],
        "Value Dt": [r.tx_date.strftime("%d-%m-%Y") for r in rows],
        "Withdrawal Amt.": [_fmt(r.debit) if r.debit > 0 else "" for r in rows],
        "Deposit Amt.": [_fmt(r.credit) if r.credit > 0 else "" for r in rows],
        "Closing Balance": [_fmt(r.balance) for r in rows],
    })


_FRAME_BUILDERS = {"sbi": to_sbi_frame, "hdfc": to_hdfc_frame}
_BANK_TITLES = {
    "sbi": "STATE BANK OF INDIA", "hdfc": "HDFC BANK LTD.",
}


def _to_bank_frame(persona: PersonaConfig, rows: list[TransactionRow]) -> pd.DataFrame:
    return _FRAME_BUILDERS[persona.statement_format](rows)


# ── File writers ──────────────────────────────────────────────────────────

def write_csv(persona: PersonaConfig, rows: list[TransactionRow], out_dir: Path) -> Path:
    frame = _to_bank_frame(persona, rows)
    csv_path = out_dir / f"{persona.name}_{persona.statement_format}_statement.csv"
    frame.to_csv(csv_path, index=False)
    return csv_path


def write_pdf(persona: PersonaConfig, rows: list[TransactionRow], out_dir: Path) -> Path:
    frame = _to_bank_frame(persona, rows)
    pdf_path = out_dir / f"{persona.name}_{persona.statement_format}_statement.pdf"
    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, leftMargin=14*mm, rightMargin=14*mm)
    styles = getSampleStyleSheet()

    bank_title = _BANK_TITLES.get(persona.statement_format, persona.statement_format.upper())
    title = Paragraph(f"<b>{bank_title}</b>", styles["Title"])
    subtitle = Paragraph(
        f"Account Statement - {persona.name.title()}<br/>{persona.notes}", styles["BodyText"])

    table_data = [list(frame.columns)] + frame.astype(str).values.tolist()
    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor("#f8fafc")]),
        ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
    ]))

    doc.build([title, Spacer(1, 6*mm), subtitle, Spacer(1, 5*mm), table])
    return pdf_path


def main() -> None:
    out_dir = Path("generated_statements")
    out_dir.mkdir(parents=True, exist_ok=True)

    generated: list[Path] = []
    for persona in PERSONAS:
        rows = generate_transactions(persona, months=6)
        generated.append(write_csv(persona, rows, out_dir))
        generated.append(write_pdf(persona, rows, out_dir))

    print("Generated synthetic statements:")
    for fp in generated:
        print(f"  {fp}")


if __name__ == "__main__":
    main()
