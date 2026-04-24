from __future__ import annotations

"""
HDFC Bank Statement Parser
==========================
HDFC exports (both PDF and CSV) use these column names:
  CSV : Date | Narration | Chq./Ref.No. | Value Dt | Withdrawal Amt. | Deposit Amt. | Closing Balance
  PDF : same columns, sometimes preceded by an account summary section.

Date format: DD-MM-YYYY (hyphen-separated)
Amount     : comma-separated Indian notation; empty string means zero for that direction.
"""

import pandas as pd

from .base import BaseStatementParser, ParsedTransaction, dataframe_to_transactions


class HDFCStatementParser(BaseStatementParser):
    bank_name = "hdfc"

    _DATE_COLS = [
        "date",
        "value_dt",
        "value_date",
        "transaction_date",
        "txn_date",
        "tran_date",
        "posting_date",
    ]
    _NARRATION_COLS = [
        "narration",
        "description",
        "particulars",
        "remarks",
        "detail",
        "details",
        "transaction_remarks",
    ]
    _DEBIT_COLS = [
        "withdrawal_amt",
        "withdrawal_amt_",       # HDFC PDF sometimes appends a trailing dot
        "withdrawal",
        "debit",
        "debit_amount",
        "dr",
        "dr_amount",
        "debit_amt",
    ]
    _CREDIT_COLS = [
        "deposit_amt",
        "deposit_amt_",
        "deposit",
        "credit",
        "credit_amount",
        "cr",
        "cr_amount",
        "credit_amt",
    ]
    _BALANCE_COLS = [
        "closing_balance",
        "balance",
        "running_balance",
        "avail_balance",
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
