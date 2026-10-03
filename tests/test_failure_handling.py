from app.execution_engine import ExecutionEngine


def test_transient_failure_retries_once():

    engine = ExecutionEngine()

    calls = []

    def fake_execute_tool(
        tool_name,
        parameters,
    ):

        calls.append(
            {
                "tool": tool_name,
                "parameters": parameters,
            }
        )

        if len(calls) == 1:

            return {
                "success": False,
                "error": (
                    "Finance system temporarily "
                    "unavailable (timeout)."
                ),
            }

        return {
            "success": True,
            "result": {
                "success": True,
                "ok": True,
            },
        }

    engine.execute_tool = fake_execute_tool

    step = {
        "step": 1,
        "tool": "update_finance_system",
        "action": "Update a finance record.",
        "parameters": {
            "invoice_id": "ACME-2026-003",
            "amount": 84500,
            "due_date": "2026-10-25",
        },
    }

    result = engine.execute_step(
        step
    )

    assert result["success"] is True
    assert len(calls) == 2

    events = [
        item["event"]
        for item in engine.execution_log
    ]

    assert "retry_started" in events
    assert "retry_succeeded" in events

    print(
        "TEST 1 - Transient failure retry: PASS"
    )


def test_semantic_failure_does_not_retry():

    engine = ExecutionEngine()

    calls = []

    def fake_execute_tool(
        tool_name,
        parameters,
    ):

        calls.append(
            {
                "tool": tool_name,
                "parameters": parameters,
            }
        )

        return {
            "success": False,
            "error": "Invoice not found.",
        }

    engine.execute_tool = fake_execute_tool

    step = {
        "step": 1,
        "tool": "read_invoice",
        "action": "Read invoice.",
        "parameters": {
            "file": (
                "data/invoices/"
                "missing_invoice.json"
            ),
        },
    }

    result = engine.execute_step(
        step
    )

    assert result["success"] is False
    assert len(calls) == 1

    events = [
        item["event"]
        for item in engine.execution_log
    ]

    assert "retry_started" not in events

    print(
        "TEST 2 - Semantic failure stops safely: PASS"
    )


if __name__ == "__main__":

    test_transient_failure_retries_once()

    test_semantic_failure_does_not_retry()

    print("")
    print(
        "FAILURE RETRY TESTS PASSED."
    )
