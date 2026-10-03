import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class InvoiceSearchTool:
    """
    Searches the simulated company invoice repository.

    The agent does not directly access the filesystem.
    It asks this tool to perform the operation.
    """

    name = "search_invoices"

    def __init__(self):
        self.invoice_directory = Path("data/invoices")

    def execute(
        self,
        company: str,
    ) -> Dict[str, Any]:

        if not self.invoice_directory.exists():
            return {
                "success": False,
                "error": "Invoice directory does not exist.",
                "results": [],
            }

        matches: List[Dict[str, Any]] = []

        for file_path in self.invoice_directory.glob("*.json"):

            try:

                with open(
                    file_path,
                    "r",
                    encoding="utf-8",
                ) as file:

                    invoice = json.load(file)

            except Exception as exc:

                continue

            invoice_company = invoice.get(
                "company",
                "",
            )

            if company.lower() in invoice_company.lower():

                matches.append(
                    {
                        "invoice_id": invoice.get(
                            "invoice_id"
                        ),
                        "company": invoice_company,
                        "invoice_date": invoice.get(
                            "invoice_date"
                        ),
                        "file": str(file_path),
                    }
                )

        matches.sort(
            key=lambda item: datetime.strptime(
                item["invoice_date"],
                "%Y-%m-%d",
            ),
            reverse=True,
        )

        return {
            "success": True,
            "company": company,
            "count": len(matches),
            "results": matches,
        }


if __name__ == "__main__":

    tool = InvoiceSearchTool()

    result = tool.execute(
        company="Acme"
    )

    print(json.dumps(
        result,
        indent=2,
    ))
