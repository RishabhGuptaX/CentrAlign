import json
from pathlib import Path
from typing import Any, Dict


class InvoiceVerificationTool:

    name = "verify_invoice"

    def __init__(self):

        self.database_path = Path(
            "data/finance/records.json"
        )

    def execute(
        self,
        invoice_id: str,
        expected_amount: float,
        expected_due_date: str,
    ) -> Dict[str, Any]:

        if not self.database_path.exists():

            return {
                "success": False,
                "verified": False,
                "error": (
                    "Finance database does not exist."
                ),
            }

        try:

            with open(
                self.database_path,
                "r",
                encoding="utf-8-sig",
            ) as file:

                database = json.load(file)

        except Exception as exc:

            return {
                "success": False,
                "verified": False,
                "error": str(exc),
            }

        records = database.get(
            "records",
            [],
        )

        matching_record = None

        for record in records:

            if record.get(
                "invoice_id"
            ) == invoice_id:

                matching_record = record
                break

        if matching_record is None:

            return {
                "success": False,
                "verified": False,
                "invoice_id": invoice_id,
                "error": (
                    "Invoice record was not found "
                    "in the finance system."
                ),
            }

        actual_amount = matching_record.get(
            "amount"
        )

        actual_due_date = matching_record.get(
            "due_date"
        )

        amount_matches = (
            float(actual_amount)
            == float(expected_amount)
        )

        due_date_matches = (
            actual_due_date
            == expected_due_date
        )

        verified = (
            amount_matches
            and due_date_matches
        )

        return {
            "success": True,
            "verified": verified,
            "invoice_id": invoice_id,
            "expected": {
                "amount": expected_amount,
                "due_date": expected_due_date,
            },
            "actual": {
                "amount": actual_amount,
                "due_date": actual_due_date,
            },
            "checks": {
                "amount_matches": amount_matches,
                "due_date_matches": due_date_matches,
            },
            "message": (
                "Invoice successfully verified."
                if verified
                else "Invoice verification failed."
            ),
        }
