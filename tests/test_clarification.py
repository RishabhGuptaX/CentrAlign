import os
import sys

sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..")
    ),
)

from app.execution_engine import ExecutionEngine


def test_missing_company_needs_clarification():
    engine = ExecutionEngine()

    result = engine.execute_task(
        "Find the latest invoice."
    )

    assert result["status"] == "needs_clarification"
    assert result["reason"] == "missing_company"
    assert result["clarification_question"]
    assert "Acme" in result["clarification_options"]
    assert "Globex" in result["clarification_options"]
    assert "Initech" in result["clarification_options"]

    assert not any(
        event.get("event") == "plan_created"
        for event in result["evidence"]
    )


def test_ambiguous_invoice_action_needs_clarification():
    engine = ExecutionEngine()

    result = engine.execute_task(
        "Handle the Acme invoice."
    )

    assert result["status"] == "needs_clarification"
    assert result["reason"] == "ambiguous_invoice_action"
    assert result["clarification_question"]
    assert len(result["clarification_options"]) == 3

    assert not any(
        event.get("event") == "plan_created"
        for event in result["evidence"]
    )


def test_clear_invoice_request_executes():
    engine = ExecutionEngine()

    result = engine.execute_task(
        "Find the latest invoice from Globex."
    )

    assert result["success"] is True
    assert result["status"] == "completed"


if __name__ == "__main__":
    test_missing_company_needs_clarification()
    test_ambiguous_invoice_action_needs_clarification()
    test_clear_invoice_request_executes()

    print("All clarification tests passed.")
