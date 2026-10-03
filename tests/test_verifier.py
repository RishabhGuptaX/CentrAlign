from app.verification.verifier import TaskVerifier

def test_invoice_verification():
    verifier = TaskVerifier()
    assert verifier.verify_invoice({"amount": 100}, {"amount": 100})
