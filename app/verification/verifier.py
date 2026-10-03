"""Outcome verification layer."""

class TaskVerifier:
    def verify_invoice(self, expected, actual):
        return expected == actual
