import json
from pathlib import Path
from typing import Any, Dict


class InvoiceReaderTool:
    """
    Reads an invoice discovered by the search tool.
    """

    name = "read_invoice"

    def execute(
        self,
        file: str,
    ) -> Dict[str, Any]:

        path = Path(file)

        if not path.exists():
            return {
                "success": False,
                "error": f"Invoice file not found: {file}",
            }

        try:

            with open(
                path,
                "r",
                encoding="utf-8",
            ) as invoice_file:

                invoice = json.load(invoice_file)

        except Exception as exc:

            return {
                "success": False,
                "error": f"Failed to read invoice: {exc}",
            }

        required_fields = [
            "invoice_id",
            "company",
            "invoice_date",
            "amount",
            "currency",
            "due_date",
        ]

        missing_fields = [
            field
            for field in required_fields
            if field not in invoice
        ]

        if missing_fields:

            return {
                "success": False,
                "error": "Invoice is missing required fields.",
                "missing_fields": missing_fields,
            }

        return {
            "success": True,
            "invoice": invoice,
            "extracted": {
                "invoice_id": invoice["invoice_id"],
                "company": invoice["company"],
                "amount": invoice["amount"],
                "currency": invoice["currency"],
                "due_date": invoice["due_date"],
            },
        }


if __name__ == "__main__":

    tool = InvoiceReaderTool()

    result = tool.execute(
        "data/invoices/acme_2026_003.json"
    )

    print(json.dumps(
        result,
        indent=2,
    ))
