"""Simulated company invoice environment."""

from pathlib import Path

INVOICE_DIR = Path("data/invoices")


def list_invoices():
    return sorted(str(p) for p in INVOICE_DIR.glob("*.json"))
