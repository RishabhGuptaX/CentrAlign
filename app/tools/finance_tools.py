"""Tools for interacting with the simulated finance application."""

class FinanceSystemTool:
    name = "finance_system"

    def update_invoice(self, invoice_id: str, amount: float, due_date: str):
        # Simulated system; persistence will be implemented next.
        return {
            "success": True,
            "invoice_id": invoice_id,
            "amount": amount,
            "due_date": due_date,
        }
