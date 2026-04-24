from __future__ import annotations

"""
Axis Bank Statement Parser
==========================
Axis Bank exports use these column names:
  CSV : Tran Date | CHQNO | Particulars | Debit | Credit | Balance | Init.Br
  PDF : same layout with an account info preamble.

Date format: DD-MM-YYYY or DD/MM/YYYY
Amount     : comma-separated Indian notation; blank = not applicable.

Notable quirks:
  - "Particulars" is the narration column (not "Description" or "Narration").
  - "Init.Br" is the initiating branch — ignored for signal derivation.
  - Multi-line narrations can appear in PDFs where text wraps into a second row.
"""

import pandas as pd

from .base import BaseStatementParser, ParsedTransaction, dataframe_to_transactions


class AxisStatementParser(BaseStatementParser):
    bank_name = "axis"

    _DATE_COLS = [
        "tran_date",
        "transaction_date",
        "txn_date",
        "trans_date",
        "date",
        "value_date",
        "posting_date",
    ]
    _NARRATION_COLS = [
        "particulars",
        "narration",
        "description",
        "remarks",
        "detail",
        "details",
        "transaction_particulars",
    ]
    _DEBIT_COLS = [
        "debit",
        "debit_amount",
        "dr",
        "withdrawal",
        "withdrawal_amt",
        "dr_amount",
    ]
    _CREDIT_COLS = [
        "credit",
        "credit_amount",
        "cr",
        "deposit",
        "deposit_amt",
        "cr_amount",
    ]
    _BALANCE_COLS = [
        "balance",
        "closing_balance",
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
