import json
from pathlib import Path
from typing import Any, Dict


class FinanceSystemTool:
    """
    Simulated internal finance application.

    Supports controlled failure injection so the worker can
    demonstrate:

    Execute
        ->
    Observe
        ->
    Detect verification failure
        ->
    Recover
        ->
    Verify again
    """

    name = "update_finance_system"

    def __init__(self):

        self.database_path = Path(
            "data/finance/records.json"
        )

        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if not self.database_path.exists():

            self._write_database(
                {
                    "records": []
                }
            )

    # ========================================================
    # DATABASE READ
    # ========================================================

    def _load_database(
        self,
    ) -> Dict[str, Any]:

        with open(
            self.database_path,
            "r",
            encoding="utf-8-sig",
        ) as file:

            return json.load(file)

    # ========================================================
    # DATABASE WRITE
    # ========================================================

    def _write_database(
        self,
        database: Dict[str, Any],
    ):

        # utf-8 without BOM
        with open(
            self.database_path,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                database,
                file,
                indent=2,
            )

    # ========================================================
    # EXECUTE UPDATE
    # ========================================================

    def execute(
        self,
        invoice_id: str,
        amount: float,
        due_date: str,
        simulate_failure: bool = False,
    ) -> Dict[str, Any]:

        try:

            database = self._load_database()

        except (
            json.JSONDecodeError,
            UnicodeDecodeError,
        ) as exc:

            return {
                "success": False,
                "error": (
                    f"Could not read finance database: {exc}"
                ),
            }

        records = database.setdefault(
            "records",
            [],
        )

        # ----------------------------------------------------
        # FAILURE INJECTION
        #
        # The operation still "executes", but the wrong
        # amount is intentionally persisted.
        #
        # Verification must catch this.
        # ----------------------------------------------------

        actual_amount = float(
            amount
        )

        failure_injected = False

        if simulate_failure:

            actual_amount = round(
                actual_amount - 5000,
                2,
            )

            failure_injected = True

        existing_record = None

        for record in records:

            if record.get(
                "invoice_id"
            ) == invoice_id:

                existing_record = record
                break

        if existing_record:

            existing_record["amount"] = (
                actual_amount
            )

            existing_record["due_date"] = (
                due_date
            )

            existing_record["updated"] = True

            action = "updated"

        else:

            new_record = {
                "invoice_id": invoice_id,
                "amount": actual_amount,
                "due_date": due_date,
                "status": "entered",
                "updated": False,
            }

            records.append(
                new_record
            )

            action = "created"

        try:

            self._write_database(
                database
            )

        except Exception as exc:

            return {
                "success": False,
                "error": (
                    f"Could not write finance database: {exc}"
                ),
            }

        return {
            "success": True,
            "action": action,
            "invoice_id": invoice_id,
            "amount": actual_amount,
            "due_date": due_date,
            "expected_amount": float(
                amount
            ),
            "failure_injected": failure_injected,
        }

    # ========================================================
    # GET RECORD
    # ========================================================

    def get_record(
        self,
        invoice_id: str,
    ) -> Dict[str, Any]:

        try:

            database = self._load_database()

        except Exception as exc:

            return {
                "success": False,
                "error": str(exc),
            }

        for record in database.get(
            "records",
            [],
        ):

            if record.get(
                "invoice_id"
            ) == invoice_id:

                return {
                    "success": True,
                    "record": record,
                }

        return {
            "success": False,
            "error": "Invoice record not found.",
        }


if __name__ == "__main__":

    tool = FinanceSystemTool()

    print()
    print("=" * 60)
    print("FINANCE SYSTEM TEST")
    print("=" * 60)

    result = tool.execute(
        invoice_id="TEST-FAILURE",
        amount=10000,
        due_date="2026-10-31",
        simulate_failure=True,
    )

    print()
    print("Update result:")

    print(
        json.dumps(
            result,
            indent=2,
        )
    )

    print()
    print("Stored record:")

    print(
        json.dumps(
            tool.get_record(
                "TEST-FAILURE"
            ),
            indent=2,
        )
    )
