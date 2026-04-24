from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
import re

import pandas as pd
import pdfplumber


# All Indian bank date formats, tried in priority order
DATE_PATTERNS = (
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d %b %Y",
    "%d %B %Y",
    "%Y-%m-%d",
    "%d/%m/%y",
    "%d-%m-%y",
)

DATE_AT_START_RE = re.compile(
    r"^\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4})\b"
)
AMOUNT_TOKEN_RE = re.compile(
    r"\(?-?(?:\d{1,3}(?:,\d{2,3})+|\d+)(?:\.\d{1,2})?\)?\s*(?:dr|cr)?",
    flags=re.IGNORECASE,
)
HEADER_TOKENS = (
    "date",
    "narration",
    "description",
    "particulars",
    "debit",
    "credit",
    "withdrawal",
    "deposit",
    "balance",
    "amount",
    "txn",
    "transaction",
)


@dataclass(frozen=True)
class ParsedTransaction:
    date: datetime
    narration: str
    debit: int
    credit: int
    balance: int | None


class ParserError(ValueError):
    """Raised when a statement cannot be parsed into usable transactions."""


def normalize_column_name(value: str) -> str:
    """Lowercase, replace non-alphanumeric runs with underscores, strip edges."""
    normalized = "".join(ch.lower() if ch.isalnum() else "_" for ch in value.strip())
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return normalized.strip("_")


def parse_date(value: object) -> datetime | None:
    """Try all known Indian bank date formats; fall back to pandas."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value

    text = str(value).strip()
    if not text or text in {"-", "—", "na", "n/a", "nan", "none"}:
        return None

    # Remove leading/trailing whitespace from cell text that may wrap
    text = " ".join(text.split())

    for pattern in DATE_PATTERNS:
        try:
            return datetime.strptime(text, pattern)
        except ValueError:
            continue

    parsed = pd.to_datetime(text, errors="coerce", dayfirst=True)
    if pd.isna(parsed):
        return None
    return parsed.to_pydatetime()


def parse_amount(value: object) -> float | None:
    """
    Parse an INR amount string handling:
    - Thousand-comma separators: 1,23,456.78
    - DR/CR suffixes
    - Parenthetical negatives (1234.00)
    - Empty/dash strings
    """
    if value is None:
        return None
    if isinstance(value, (int, float)) and not pd.isna(value):
        return float(value)

    text = str(value).strip()
    if not text or text in {"-", "—", "na", "n/a", "nan", "none", ""}:
        return None

    negative = False
    lower = text.lower()
    if lower.endswith("dr"):
        negative = True
        text = text[:-2].strip()
    elif lower.endswith("cr"):
        text = text[:-2].strip()

    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1]

    # Remove currency symbols and thousand separators
    cleaned = re.sub(r"[^\d.\-]", "", text)
    if not cleaned or cleaned == ".":
        return None

    # Guard against multiple decimal points (malformed PDF extraction)
    parts = cleaned.split(".")
    if len(parts) > 2:
        cleaned = parts[0] + "." + "".join(parts[1:])

    try:
        amount = float(cleaned)
    except ValueError:
        return None

    if negative and amount > 0:
        amount *= -1
    return amount


def read_csv_bytes(content: bytes) -> pd.DataFrame:
    """Read CSV, trying UTF-8 then latin-1; skip blank rows."""
    for encoding in ("utf-8", "latin-1", "utf-8-sig"):
        try:
            frame = pd.read_csv(BytesIO(content), encoding=encoding, dtype=str)
            frame = frame.dropna(how="all")
            # Drop rows that are entirely whitespace
            frame = frame[~frame.apply(lambda r: r.str.strip().eq("").all(), axis=1)]
            return frame
        except UnicodeDecodeError:
            continue
        except Exception:
            break
    raise ParserError("Could not decode the uploaded CSV file.")


def _skip_preamble_rows(rows: list[list[str | None]], max_skip: int = 30) -> list[list[str | None]]:
    """
    Bank PDFs often have 10-25 rows of account metadata before the actual
    transaction table header. Find the first row that looks like a header
    (contains date/narration/debit/credit keywords) and return from there.
    """
    header_tokens = {
        "date", "narration", "description", "particulars", "debit",
        "credit", "withdrawal", "deposit", "balance", "amount",
        "txn", "tran", "transaction",
    }
    for idx, row in enumerate(rows[:max_skip]):
        cells = [str(c or "").strip().lower() for c in row]
        matches = sum(1 for cell in cells if any(tok in cell for tok in header_tokens))
        if matches >= 2:
            return rows[idx:]
    return rows


def _is_header_line(line: str) -> bool:
    lowered = line.lower()
    token_hits = sum(1 for token in HEADER_TOKENS if token in lowered)
    return token_hits >= 2


def _rows_from_pdf_text(raw_text: str) -> list[dict[str, object]]:
    """
    Fallback extractor for text-based PDFs where table extraction fails.

    It parses line-oriented transactions that start with a date and usually
    end with amount columns. This is intentionally permissive to support
    non-ruled statements where pdfplumber.extract_tables() returns nothing.
    """
    parsed_rows: list[dict[str, object]] = []
    for raw_line in raw_text.splitlines():
        line = " ".join((raw_line or "").split())
        if not line:
            continue
        if _is_header_line(line):
            continue

        date_match = DATE_AT_START_RE.match(line)
        if not date_match:
            # Treat non-date lines as narration continuations for the
            # previous transaction if they look like plain text.
            if parsed_rows and not AMOUNT_TOKEN_RE.search(line):
                previous = str(parsed_rows[-1].get("narration") or "").strip()
                parsed_rows[-1]["narration"] = f"{previous} {line}".strip()
            continue

        date_text = date_match.group(1).strip()
        remainder = line[date_match.end() :].strip(" -|")
        if not remainder:
            continue

        amount_matches = list(AMOUNT_TOKEN_RE.finditer(remainder))
        if not amount_matches:
            continue

        tail_amounts = amount_matches[-3:]
        narration_end = tail_amounts[0].start()
        narration = remainder[:narration_end].strip(" -|")
        if not narration:
            narration = "Transaction"

        amount_texts = [match.group(0).strip() for match in tail_amounts]
        debit = 0.0
        credit = 0.0
        balance: int | None = None

        if len(amount_texts) >= 3:
            debit = abs(parse_amount(amount_texts[-3]) or 0.0)
            credit = abs(parse_amount(amount_texts[-2]) or 0.0)
            balance_amount = parse_amount(amount_texts[-1])
            balance = int(round(balance_amount)) if balance_amount is not None else None
        elif len(amount_texts) == 2:
            amount_value = parse_amount(amount_texts[-2])
            balance_amount = parse_amount(amount_texts[-1])
            if amount_value is None:
                continue
            amount_lower = amount_texts[-2].lower()
            if "dr" in amount_lower or amount_value < 0:
                debit = abs(amount_value)
            else:
                credit = abs(amount_value)
            balance = int(round(balance_amount)) if balance_amount is not None else None
        else:
            amount_value = parse_amount(amount_texts[-1])
            if amount_value is None:
                continue
            amount_lower = amount_texts[-1].lower()
            if "dr" in amount_lower or amount_value < 0:
                debit = abs(amount_value)
            else:
                credit = abs(amount_value)

        if debit == 0 and credit == 0:
            continue

        parsed_rows.append(
            {
                "date": date_text,
                "narration": narration,
                "debit": debit,
                "credit": credit,
                "balance": balance,
            }
        )

    return parsed_rows


def read_pdf_tables(content: bytes) -> tuple[pd.DataFrame, str]:
    """
    Extract all tables from every PDF page, concatenate them, and return
    (combined_dataframe, full_text).

    Strategy:
    1. Try pdfplumber's table extraction with lattice and stream settings.
    2. Skip metadata preamble rows that appear before the transaction header.
    3. Concatenate pages, re-using the first page's header for all.
    """
    table_frames: list[pd.DataFrame] = []
    extracted_text: list[str] = []
    column_header: list[str] | None = None

    table_settings = {
        "vertical_strategy": "lines_strict",
        "horizontal_strategy": "lines_strict",
        "snap_tolerance": 5,
        "join_tolerance": 3,
    }
    stream_settings = {
        "vertical_strategy": "text",
        "horizontal_strategy": "text",
        "snap_tolerance": 5,
    }

    with pdfplumber.open(BytesIO(content)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            if page_text:
                extracted_text.append(page_text)

            # Try lattice (ruled lines) first, fall back to stream (whitespace)
            tables = page.extract_tables(table_settings) or []
            if not tables:
                tables = page.extract_tables(stream_settings) or []
            if not tables:
                tables = page.extract_tables() or []

            for table in tables:
                rows = [row for row in table if row and any((cell or "").strip() for cell in row)]
                if len(rows) < 2:
                    continue

                rows = _skip_preamble_rows(rows)
                if len(rows) < 2:
                    continue

                raw_header = [str(cell or "").strip() for cell in rows[0]]

                # Determine if this page is a continuation (same header repeated)
                is_continuation = (
                    column_header is not None
                    and raw_header == column_header
                )

                if column_header is None:
                    column_header = raw_header

                # Body rows are everything after the header row
                body_start = 1 if (column_header == raw_header or not is_continuation) else 0
                body = rows[body_start:]
                if not body:
                    continue

                # Pad or truncate rows to match header width
                ncols = len(column_header)
                padded_body = [
                    (row + [None] * ncols)[:ncols] for row in body
                ]

                frame = pd.DataFrame(padded_body, columns=column_header)
                frame = frame.dropna(how="all")
                if not frame.empty:
                    table_frames.append(frame)

    full_text = "\n".join(extracted_text)
    if not table_frames:
        fallback_rows = _rows_from_pdf_text(full_text)
        if fallback_rows:
            fallback_frame = pd.DataFrame(fallback_rows)
            fallback_frame = fallback_frame.dropna(how="all")
            if not fallback_frame.empty:
                return fallback_frame, full_text
        raise ParserError(
            "No tabular transaction data could be extracted from the uploaded PDF statement. "
            "The file may be scanned/image-only or use a non-readable layout."
        )

    combined = pd.concat(table_frames, ignore_index=True)
    combined = combined.dropna(how="all")
    if combined.empty:
        raise ParserError("Extracted PDF tables were empty after cleaning.")

    return combined, full_text


def normalize_frame_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with all column names normalized to snake_case."""
    normalized = frame.copy()
    normalized.columns = [normalize_column_name(str(col)) for col in normalized.columns]
    return normalized


def find_column(columns: list[str], candidates: list[str]) -> str | None:
    """
    Find the first matching column.

    Priority:
    1. Exact match after normalization
    2. Candidate is a substring of a column name
    3. Column name is a substring of a candidate
    """
    for candidate in candidates:
        if candidate in columns:
            return candidate
    for candidate in candidates:
        for column in columns:
            if candidate in column:
                return column
    for candidate in candidates:
        for column in columns:
            if column in candidate:
                return column
    return None


def dataframe_to_transactions(
    frame: pd.DataFrame,
    *,
    date_candidates: list[str],
    narration_candidates: list[str],
    debit_candidates: list[str],
    credit_candidates: list[str],
    balance_candidates: list[str],
    amount_candidates: list[str],
    type_candidates: list[str],
) -> list[ParsedTransaction]:
    """
    Convert a bank statement DataFrame (raw or normalized) into ParsedTransaction
    objects. Handles both split debit/credit columns and single amount+type columns.
    """
    if frame.empty:
        raise ParserError("Statement contains no rows.")

    working = normalize_frame_columns(frame).dropna(how="all")
    columns = working.columns.tolist()

    date_col = find_column(columns, date_candidates)
    narration_col = find_column(columns, narration_candidates)
    debit_col = find_column(columns, debit_candidates)
    credit_col = find_column(columns, credit_candidates)
    balance_col = find_column(columns, balance_candidates)
    amount_col = find_column(columns, amount_candidates)
    type_col = find_column(columns, type_candidates)

    if not date_col:
        raise ParserError(
            f"Could not detect the transaction date column. "
            f"Available columns: {columns}"
        )

    parsed_rows: list[ParsedTransaction] = []

    for _, row in working.iterrows():
        txn_date = parse_date(row.get(date_col))
        if not txn_date:
            continue

        narration = str(row.get(narration_col) or "").strip() if narration_col else ""
        # Collapse internal newlines that PDF extraction can produce
        narration = " ".join(narration.split())

        debit_value = parse_amount(row.get(debit_col)) if debit_col else None
        credit_value = parse_amount(row.get(credit_col)) if credit_col else None

        # If separate debit/credit columns are both empty, try the amount+type pattern
        if amount_col and debit_value is None and credit_value is None:
            amount_value = parse_amount(row.get(amount_col))
            if amount_value is not None:
                if type_col:
                    tx_type = str(row.get(type_col) or "").strip().lower()
                    if any(token in tx_type for token in ("dr", "debit", "withdraw")):
                        debit_value = abs(amount_value)
                        credit_value = 0.0
                    elif any(token in tx_type for token in ("cr", "credit", "deposit")):
                        credit_value = abs(amount_value)
                        debit_value = 0.0
                    elif amount_value < 0:
                        debit_value = abs(amount_value)
                        credit_value = 0.0
                    else:
                        credit_value = abs(amount_value)
                        debit_value = 0.0
                elif amount_value < 0:
                    debit_value = abs(amount_value)
                    credit_value = 0.0
                else:
                    credit_value = abs(amount_value)
                    debit_value = 0.0

        debit = int(round(abs(debit_value or 0.0)))
        credit = int(round(abs(credit_value or 0.0)))
        if debit == 0 and credit == 0:
            continue

        balance_value = parse_amount(row.get(balance_col)) if balance_col else None
        balance = None if balance_value is None else int(round(balance_value))

        parsed_rows.append(
            ParsedTransaction(
                date=txn_date,
                narration=narration,
                debit=debit,
                credit=credit,
                balance=balance,
            )
        )

    if not parsed_rows:
        raise ParserError(
            "No valid transaction rows could be parsed. "
            "Check that the statement is not password-protected or image-only."
        )

    parsed_rows.sort(key=lambda item: item.date)
    return parsed_rows


class BaseStatementParser(ABC):
    """Abstract base class for all bank statement parsers."""

    bank_name: str = "generic"

    def parse(self, filename: str, content: bytes) -> list[ParsedTransaction]:
        """
        Entry point: detect file type, extract raw tabular data, then
        delegate to parse_dataframe() for bank-specific column mapping.
        """
        extension = Path(filename or "").suffix.lower()

        if extension == ".csv":
            frame = read_csv_bytes(content)
            return self.parse_dataframe(frame)

        if extension == ".pdf":
            frame, raw_text = read_pdf_tables(content)
            return self.parse_dataframe(frame)

        raise ParserError(
            f"Unsupported statement format '{extension}'. "
            "Please upload a PDF or CSV bank statement."
        )

    @abstractmethod
    def parse_dataframe(self, frame: pd.DataFrame) -> list[ParsedTransaction]:
        """Convert a bank statement table into normalized transactions."""
