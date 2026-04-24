from __future__ import annotations

"""
ICICI Bank Statement Parser
============================
ICICI Bank iMobile/NetBanking CSV exports use these column names:
  CSV : Transaction Date | Value Date | Description | Ref No | Withdrawals | Deposits | Balance
  PDF : Same columns. Some older ICICI exports label columns as:
        "S No.", "Value Date", "Transaction Date", "Cheque Number",
        "Transaction Remarks", "Withdrawals (Dr)", "Deposit (Cr)", "Balance (INR)"

Date format: DD/MM/YYYY  (slash-separated)
Amount     : Indian comma notation; negative amounts indicate debits in some exports.

Notable quirks:
  - ICICI uses "Withdrawals" / "Deposits" (plural) instead of Debit/Credit.
  - Older PDF statements use "Withdrawals (Dr)" / "Deposit (Cr)" with parenthetical labels.
  - The description column is sometimes labelled "Transaction Remarks".
"""

import pandas as pd

from .base import BaseStatementParser, ParsedTransaction, dataframe_to_transactions


class ICICIStatementParser(BaseStatementParser):
    bank_name = "icici"

    _DATE_COLS = [
        "transaction_date",
        "value_date",
        "txn_date",
        "date",
        "trans_date",
        "posting_date",
    ]
    _NARRATION_COLS = [
        "transaction_remarks",
        "description",
        "particulars",
        "narration",
        "remarks",
        "detail",
        "details",
    ]
    _DEBIT_COLS = [
        "withdrawals",
        "withdrawal",
        "withdrawals_dr",
        "debit",
        "debit_amount",
        "dr",
        "dr_amount",
        "debit_amt",
    ]
    _CREDIT_COLS = [
        "deposits",
        "deposit",
        "deposit_cr",
        "credit",
        "credit_amount",
        "cr",
        "cr_amount",
        "credit_amt",
    ]
    _BALANCE_COLS = [
        "balance",
        "balance_inr",
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
