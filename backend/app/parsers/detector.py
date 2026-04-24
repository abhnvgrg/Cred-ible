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


# ---------------------------------------------------------------------------
# Keyword fingerprints per bank.
# Higher-weight keywords (more unique to a bank) are listed first.
# Each keyword that appears in the haystack contributes +1 to that bank's score.
# ---------------------------------------------------------------------------
BANK_KEYWORDS: dict[str, tuple[str, ...]] = {
    "sbi": (
        "state bank of india",
        "sbi",
        "ref no./cheque no",          # exact SBI CSV header fragment
        "txn date",                   # SBI date column name
        "sbiin",                      # SBI SWIFT / IFSC prefix
        "yono",                       # SBI's app name
        "branch code",
    ),
    "hdfc": (
        "hdfc bank",
        "hdfc",
        "withdrawal amt",             # HDFC CSV column fragment
        "deposit amt",
        "chq./ref.no",                # HDFC cheque column
        "hdfcbank",
        "value dt",                   # HDFC value-date column abbreviation
    ),
    "axis": (
        "axis bank",
        "axis",
        "tran date",                  # Axis date column name
        "particulars",                # Axis narration column
        "init.br",                    # Axis initiating-branch column
        "axisbank",
        "chqno",                      # Axis cheque column
    ),
    "icici": (
        "icici bank",
        "icici",
        "withdrawals",                # ICICI debit column (plural)
        "deposits",                   # ICICI credit column (plural)
        "transaction remarks",        # ICICI description label
        "icicibank",
        "imobile",
        "balance(inr)",
        "balance (inr)",
    ),
}

# Minimum score to accept a bank detection (avoids false positives on generic words)
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
    """Extract a plain-text preview suitable for keyword matching."""
    extension = Path(filename or "").suffix.lower()

    if extension == ".pdf":
        try:
            with pdfplumber.open(BytesIO(content)) as pdf:
                texts: list[str] = []
                # Read first 3 pages to catch account info that appears late
                for page in pdf.pages[:3]:
                    page_text = page.extract_text() or ""
                    if page_text:
                        texts.append(page_text)
                    # Also read first-page table headers for keyword matching
                    tables = page.extract_tables() or []
                    for table in tables[:1]:
                        if table and table[0]:
                            texts.append(" ".join(str(c or "") for c in table[0]))
                return "\n".join(texts)
        except Exception:
            return ""

    if extension == ".csv":
        try:
            # Read enough to cover the header + a few data rows
            return content.decode("utf-8", errors="ignore")[:8000]
        except Exception:
            return ""

    return ""


def detect_bank(filename: str, content: bytes) -> str:
    """
    Return the most likely bank name ('sbi', 'hdfc', 'axis', 'icici', 'generic').
    """
    preview = _extract_preview_text(filename, content)
    haystack = f"{filename}\n{preview}".lower()

    scored: list[tuple[int, str]] = []
    for bank, keywords in BANK_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in haystack)
        scored.append((score, bank))

    best_score, best_bank = max(scored, key=lambda item: item[0])
    if best_score < _MIN_DETECTION_SCORE:
        return "generic"

    # Tie-break: if two banks share the top score, prefer generic to avoid wrong parser
    top_scorers = [bank for score, bank in scored if score == best_score]
    if len(top_scorers) > 1:
        return "generic"

    return best_bank


def parse_statement_transactions(filename: str, content: bytes) -> ParseDetectionResult:
    """
    Main entry point: detect bank, attempt bank-specific parse,
    fall back to generic parser on failure.
    """
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
            # Already tried generic — re-raise with the original message
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
            # Neither bank-specific nor generic could parse it — surface the
            # original, more-descriptive error
            raise primary_error
