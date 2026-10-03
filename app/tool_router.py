from typing import Any, Dict

from app.tools.invoice_search import InvoiceSearchTool
from app.tools.invoice_reader import InvoiceReaderTool
from app.tools.finance_system import FinanceSystemTool
from app.tools.invoice_verification import InvoiceVerificationTool
from app.tools.human_approval import HumanApprovalTool


class ToolRouter:
    """
    Central registry and dispatcher for all tools available
    to the autonomous worker.
    """

    def __init__(self):

        self.tools = {
            "search_invoices": InvoiceSearchTool(),
            "read_invoice": InvoiceReaderTool(),
            "update_finance_system": FinanceSystemTool(),
            "verify_invoice": InvoiceVerificationTool(),
            "request_human_approval": HumanApprovalTool(),
        }

    def list_tools(self):
        return list(self.tools.keys())

    def execute(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:

        if tool_name not in self.tools:

            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}",
                "tool": tool_name,
            }

        tool = self.tools[tool_name]

        try:

            result = tool.execute(
                **parameters
            )

            return {
                "tool": tool_name,
                "success": result.get(
                    "success",
                    False,
                ),
                "result": result,
            }

        except Exception as exc:

            return {
                "tool": tool_name,
                "success": False,
                "error": str(exc),
            }


if __name__ == "__main__":

    router = ToolRouter()

    print("Available tools:")

    for tool in router.list_tools():
        print(f" - {tool}")

    print()
    print("Testing invoice search...")

    result = router.execute(
        "search_invoices",
        {
            "company": "Acme",
        },
    )

    print(result)
