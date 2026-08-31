from __future__ import annotations

"""
Bank Format Auto-Detector
==========================
Detects the issuing bank from filename, PDF text, and CSV header content.

Detection algorithm:
  1. Build a "haystack" from the filename + first-page text (PDF) or first
     6 KB of content (CSV).
  2. Score each known bank by how many of its keyword fingerprints appear.
  3. Return the bank with the highest score; fall back to "generic" on a tie
     at zero or if only one keyword matched (too ambiguous).

Fallback behaviour (in parse_statement_transactions):
  - If the detected bank's parser fails with a ParserError, the generic
    parser is tried automatically and a warning is added to the result.
"""

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import pdfplumber

from .axis import AxisStatementParser
from .base import BaseStatementParser, ParsedTransaction, ParserError
from .generic import GenericStatementParser
from .hdfc import HDFCStatementParser
from .icici import ICICIStatementParser
from .sbi import SBIStatementParser


@dataclass(frozen=True)
class ParseDetectionResult:
    detected_bank: str
    parser_name: str
    transactions: list[ParsedTransaction]
    warnings: list[str]


BANK_KEYWORDS: dict[str, tuple[str, ...]] = {
    "sbi": (
        "state bank of india",
        "sbi",
        "ref no./cheque no",
        "txn date",
        "sbiin",
        "yono",
        "branch code",
    ),
    "hdfc": (
        "hdfc bank",
        "hdfc",
        "withdrawal amt",
        "deposit amt",
        "chq./ref.no",
        "hdfcbank",
        "value dt",
    ),
    "axis": (
        "axis bank",
        "axis",
        "tran date",
        "particulars",
        "init.br",
        "axisbank",
        "chqno",
    ),
    "icici": (
        "icici bank",
        "icici",
        "withdrawals",
        "deposits",
        "transaction remarks",
        "icicibank",
        "imobile",
        "balance(inr)",
        "balance (inr)",
    ),
}

_MIN_DETECTION_SCORE = 1


def _build_parser(bank: str) -> BaseStatementParser:
    if bank == "sbi":
        return SBIStatementParser()
    if bank == "hdfc":
        return HDFCStatementParser()
    if bank == "axis":
        return AxisStatementParser()
    if bank == "icici":
        return ICICIStatementParser()
    return GenericStatementParser()


def _extract_preview_text(filename: str, content: bytes) -> str:
    extension = Path(filename or "").suffix.lower()

    if extension == ".pdf":
        try:
            with pdfplumber.open(BytesIO(content)) as pdf:
                texts: list[str] = []
                for page in pdf.pages[:3]:
                    page_text = page.extract_text() or ""
                    if page_text:
                        texts.append(page_text)
                    tables = page.extract_tables() or []
                    for table in tables[:1]:
                        if table and table[0]:
                            texts.append(" ".join(str(c or "") for c in table[0]))
                return "\n".join(texts)
        except Exception:
            return ""

    if extension == ".csv":
        try:
            return content.decode("utf-8", errors="ignore")[:8000]
        except Exception:
            return ""

    return ""


def detect_bank(filename: str, content: bytes) -> str:
    preview = _extract_preview_text(filename, content)
    haystack = f"{filename}\n{preview}".lower()

    scored: list[tuple[int, str]] = []
    for bank, keywords in BANK_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in haystack)
        scored.append((score, bank))

    best_score, best_bank = max(scored, key=lambda item: item[0])
    if best_score < _MIN_DETECTION_SCORE:
        return "generic"

    top_scorers = [bank for score, bank in scored if score == best_score]
    if len(top_scorers) > 1:
        return "generic"

    return best_bank


def parse_statement_transactions(filename: str, content: bytes) -> ParseDetectionResult:
    detected_bank = detect_bank(filename, content)
    parser = _build_parser(detected_bank)
    warnings: list[str] = []

    try:
        transactions = parser.parse(filename=filename, content=content)
        return ParseDetectionResult(
            detected_bank=detected_bank,
            parser_name=parser.bank_name,
            transactions=transactions,
            warnings=warnings,
        )
    except ParserError as primary_error:
        if detected_bank == "generic":
            raise

        fallback_parser = GenericStatementParser()
        try:
            transactions = fallback_parser.parse(filename=filename, content=content)
            warnings.append(
                f"{detected_bank.upper()} format parser failed; "
                f"generic parser was used as fallback. Detail: {primary_error}"
            )
            return ParseDetectionResult(
                detected_bank=detected_bank,
                parser_name=fallback_parser.bank_name,
                transactions=transactions,
                warnings=warnings,
            )
        except ParserError:
            raise primary_error
