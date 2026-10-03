"""Simulated internal finance application."""

class FinanceApp:
    def __init__(self):
        self.records = {}

    def update(self, invoice_id, amount, due_date):
        self.records[invoice_id] = {
            "amount": amount,
            "due_date": due_date,
        }
        return self.records[invoice_id]

    def get(self, invoice_id):
        return self.records.get(invoice_id)
