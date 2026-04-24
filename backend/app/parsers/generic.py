from __future__ import annotations

"""
Generic Fallback Statement Parser
==================================
Used when the bank cannot be auto-detected.  Attempts the broadest possible
set of column aliases so it can handle exports from cooperative banks, NBFCs,
payment wallets, and any institution that wasn't explicitly listed.

Strategy:
  1. Try every known alias for each semantic column type.
  2. Also try to infer debit vs. credit from a single "Amount" column combined
     with a "Type" / "Dr/Cr" indicator column.
  3. If no amount column is found at all, raise a clear ParserError.
"""

import pandas as pd

from .base import BaseStatementParser, ParsedTransaction, dataframe_to_transactions


class GenericStatementParser(BaseStatementParser):
    bank_name = "generic"

    _DATE_COLS = [
        "transaction_date",
        "txn_date",
        "tran_date",
        "trans_date",
        "date",
        "value_date",
        "posting_date",
        "posted_on",
        "booking_date",
        "process_date",
        "entry_date",
        "dt",
    ]
    _NARRATION_COLS = [
        "narration",
        "description",
        "particulars",
        "remarks",
        "detail",
        "details",
        "transaction_remarks",
        "transaction_details",
        "trans_desc",
        "txn_description",
        "memo",
        "narrative",
        "reference",
        "notes",
    ]
    _DEBIT_COLS = [
        "debit",
        "withdrawal",
        "withdrawals",
        "withdrawal_amt",
        "debit_amount",
        "debit_amt",
        "dr",
        "dr_amount",
        "withdrawals_dr",
        "paid_out",
        "money_out",
        "outflow",
    ]
    _CREDIT_COLS = [
        "credit",
        "deposit",
        "deposits",
        "deposit_amt",
        "credit_amount",
        "credit_amt",
        "cr",
        "cr_amount",
        "deposit_cr",
        "paid_in",
        "money_in",
        "inflow",
    ]
    _BALANCE_COLS = [
        "balance",
        "closing_balance",
        "running_balance",
        "avail_balance",
        "available_balance",
        "book_balance",
        "balance_inr",
        "ledger_balance",
        "end_balance",
    ]
    _AMOUNT_COLS = [
        "amount",
        "transaction_amount",
        "txn_amount",
        "trans_amount",
        "value",
        "net_amount",
    ]
    _TYPE_COLS = [
        "dr_cr",
        "transaction_type",
        "txn_type",
        "trans_type",
        "type",
        "debit_credit",
        "indicator",
        "cr_dr",
    ]

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
