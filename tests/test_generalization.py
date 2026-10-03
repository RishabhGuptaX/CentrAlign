import json

from app.execution_engine import ExecutionEngine


def print_result(name, result):
    print()
    print("=" * 78)
    print(name)
    print("=" * 78)

    print(
        json.dumps(
            {
                "success": result.get("success"),
                "status": result.get("status"),
                "run_id": result.get("run_id"),
                "goal": result.get("goal"),
                "recovery_used": result.get("recovery_used"),
                "approval_used": result.get("approval_used"),
                "resumed_from_pause": result.get(
                    "resumed_from_pause"
                ),
                "steps": len(
                    result.get("step_results", [])
                ),
            },
            indent=2,
            default=str,
        )
    )


def assert_completed(name, result):
    if not result.get("success"):
        raise AssertionError(
            f"{name} failed: "
            f"{result.get('status')} | "
            f"{result.get('error', '')}"
        )

    if result.get("status") != "completed":
        raise AssertionError(
            f"{name} expected status=completed, "
            f"got {result.get('status')}"
        )


def run_generalization_tests():

    # ========================================================
    # TEST 1 - DIFFERENT COMPANY
    # ========================================================

    task_1 = (
        "Find the latest invoice from Globex."
    )

    engine_1 = ExecutionEngine()

    result_1 = engine_1.execute_task(
        task_1,
        simulate_failure=False,
        approval_granted=False,
    )

    print_result(
        "TEST 1 - Globex invoice lookup",
        result_1,
    )

    assert_completed(
        "Globex invoice lookup",
        result_1,
    )


    # ========================================================
    # TEST 2 - DIFFERENT COMPANY + EXTRACTION
    # ========================================================

    task_2 = (
        "Find the latest invoice from Initech, "
        "extract the amount and due date, and verify "
        "the invoice information."
    )

    engine_2 = ExecutionEngine()

    result_2 = engine_2.execute_task(
        task_2,
        simulate_failure=False,
        approval_granted=False,
    )

    print_result(
        "TEST 2 - Initech extraction and verification",
        result_2,
    )

    assert_completed(
        "Initech workflow",
        result_2,
    )


    # ========================================================
    # TEST 3 - VERIFICATION ONLY
    # ========================================================

    task_3 = (
        "Verify that the latest Acme invoice is correctly "
        "recorded in the internal finance system."
    )

    engine_3 = ExecutionEngine()

    result_3 = engine_3.execute_task(
        task_3,
        simulate_failure=False,
        approval_granted=False,
    )

    print_result(
        "TEST 3 - Acme verification task",
        result_3,
    )

    assert_completed(
        "Acme verification",
        result_3,
    )


    # ========================================================
    # TEST 4A - HUMAN APPROVAL
    # ========================================================

    task_4 = (
        "Find the latest invoice from Acme, "
        "extract the amount and due date, "
        "enter it into the internal finance system, "
        "and verify that the update was completed correctly."
    )

    engine_4 = ExecutionEngine()

    pending = engine_4.execute_task(
        task_4,
        simulate_failure=False,
        approval_granted=False,
    )

    print_result(
        "TEST 4A - High-value task pauses for approval",
        pending,
    )

    if pending.get(
        "status"
    ) != "awaiting_human_approval":

        raise AssertionError(
            "Expected high-value Acme task "
            "to pause for human approval."
        )


    # ========================================================
    # TEST 4B - RESUME AFTER APPROVAL
    # ========================================================

    resumed_engine = ExecutionEngine()

    approved = resumed_engine.execute_task(
        task_4,
        simulate_failure=False,
        approval_granted=True,
    )

    print_result(
        "TEST 4B - Approved task resumes",
        approved,
    )

    assert_completed(
        "Approval resume",
        approved,
    )

    if not approved.get(
        "resumed_from_pause"
    ):

        raise AssertionError(
            "Expected resumed_from_pause=True."
        )


    # ========================================================
    # TEST 5 - FAILURE + RECOVERY
    # ========================================================

    engine_5 = ExecutionEngine()

    result_5 = engine_5.execute_task(
        task_4,
        simulate_failure=True,
        approval_granted=True,
    )

    print_result(
        "TEST 5 - Failure injection and recovery",
        result_5,
    )

    assert_completed(
        "Recovery workflow",
        result_5,
    )

    if not result_5.get(
        "recovery_used"
    ):

        raise AssertionError(
            "Expected recovery_used=True."
        )


    # ========================================================
    # FINAL RESULT
    # ========================================================

    print()
    print("=" * 78)
    print("ALL GENERALIZATION TESTS PASSED")
    print("=" * 78)

    print(
        "Different company lookup: PASS"
    )

    print(
        "Different company extraction: PASS"
    )

    print(
        "Verification-only workflow: PASS"
    )

    print(
        "Human approval + resume: PASS"
    )

    print(
        "Failure detection + recovery: PASS"
    )


if __name__ == "__main__":
    run_generalization_tests()
