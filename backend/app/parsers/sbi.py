from __future__ import annotations

"""
SBI Bank Statement Parser
=========================
SBI exports (both PDF and CSV) use these column names:
  CSV : Txn Date | Value Date | Description | Ref No./Cheque No. | Debit | Credit | Balance
  PDF : same columns, but may have 10–20 preamble rows before the table header.

Date format: DD/MM/YYYY (slash-separated)
Amount     : comma-separated Indian notation, e.g. 1,23,456.00
             Empty cell means the column did not apply for that row.
"""

import pandas as pd

from .base import BaseStatementParser, ParsedTransaction, dataframe_to_transactions


class SBIStatementParser(BaseStatementParser):
    bank_name = "sbi"

    # ------------------------------------------------------------------
    # Column aliases — most-specific first so find_column() picks the
    # exact SBI name before falling back to generics.
    # ------------------------------------------------------------------
    _DATE_COLS = [
        "txn_date",
        "transaction_date",
        "tran_date",
        "date",
        "value_date",
        "posting_date",
    ]
    _NARRATION_COLS = [
        "description",
        "narration",
        "particulars",
        "remarks",
        "detail",
        "details",
    ]
    _DEBIT_COLS = [
        "debit",
        "debit_amount",
        "withdrawal",
        "withdrawal_amt",
        "dr",
        "dr_amount",
    ]
    _CREDIT_COLS = [
        "credit",
        "credit_amount",
        "deposit",
        "deposit_amt",
        "cr",
        "cr_amount",
    ]
    _BALANCE_COLS = [
        "balance",
        "closing_balance",
        "running_balance",
        "avail_balance",
        "book_balance",
    ]
    _AMOUNT_COLS = ["amount", "transaction_amount", "txn_amount"]
    _TYPE_COLS = ["dr_cr", "transaction_type", "type", "txn_type"]

    def parse_dataframe(self, frame: pd.DataFrame) -> list[ParsedTransaction]:
        return dataframe_to_transactions(
            frame,
            date_candidates=self._DATE_COLS,
            narration_candidates=self._NARRATION_COLS,
            debit_candidates=self._DEBIT_COLS,
            credit_candidates=self._CREDIT_COLS,
            balance_candidates=self._BALANCE_COLS,
            amount_candidates=self._AMOUNT_COLS,
            type_candidates=self._TYPE_COLS,
        )
