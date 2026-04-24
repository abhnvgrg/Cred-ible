from __future__ import annotations

from dataclasses import dataclass

from .detector import ParseDetectionResult, parse_statement_transactions
from .signals import DerivedSignalResult, derive_signals


@dataclass(frozen=True)
class StatementParseResult:
    detected_bank: str
    statement_months: int
    confidence_score: float
    low_history_warning: bool
    income_undetectable: bool
    upi_inactive: bool
    parsed_signals: dict[str, int | float]
    parser_warnings: list[str]


def parse_statement_file(filename: str, content: bytes, borrower_name: str) -> StatementParseResult:
    """
    Top-level orchestrator: detect bank → parse transactions → derive signals.

    This is the single function called by the /parse/statement route handler.
    It never raises unhandled exceptions — ParserError and ValueError bubble up
    to the route handler which converts them to 422 responses with field-level detail.
    """
    detection: ParseDetectionResult = parse_statement_transactions(
        filename=filename,
        content=content,
    )
    derived: DerivedSignalResult = derive_signals(
        detection.transactions,
        borrower_name=borrower_name,
    )
    warnings = [*detection.warnings, *derived.warnings]

    return StatementParseResult(
        detected_bank=detection.detected_bank,
        statement_months=derived.statement_months,
        confidence_score=derived.confidence_score,
        low_history_warning=derived.low_history_warning,
        income_undetectable=derived.income_undetectable,
        upi_inactive=derived.upi_inactive,
        parsed_signals=derived.signals,
        parser_warnings=warnings,
    )


__all__ = [
    "StatementParseResult",
    "parse_statement_file",
]
