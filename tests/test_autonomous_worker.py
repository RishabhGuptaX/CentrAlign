import json
from app.execution_engine import ExecutionEngine


TEST_CASES = [

    {
        "name": "Acme latest invoice",
        "task": (
            "Find the latest invoice from Acme, "
            "extract the amount and due date, "
            "enter it into the internal finance system, "
            "and verify that the update was completed correctly."
        ),
    },

    {
        "name": "Acme invoice lookup",
        "task": (
            "Find the most recent Acme invoice and "
            "record its amount and due date in the finance system."
        ),
    },

    {
        "name": "Finance verification",
        "task": (
            "Find the latest Acme invoice, update the finance system "
            "with its amount and due date, then verify the record."
        ),
    },
]


def run_test(test_case):

    print()
    print("=" * 75)
    print(f"TEST: {test_case['name']}")
    print("=" * 75)

    engine = ExecutionEngine()

    result = engine.execute_task(
        test_case["task"]
    )

    summary = {
        "test": test_case["name"],
        "success": result.get("success"),
        "status": result.get("status"),
        "failed_step": result.get("failed_step"),
        "steps_completed": len(
            result.get(
                "step_results",
                [],
            )
        ),
    }

    print()
    print("-" * 75)
    print("TEST SUMMARY")
    print("-" * 75)

    print(
        json.dumps(
            summary,
            indent=2,
        )
    )

    return summary


if __name__ == "__main__":

    print()
    print("=" * 75)
    print("CENTRALIGN - AUTONOMOUS WORKER TEST SUITE")
    print("=" * 75)

    summaries = []

    for test_case in TEST_CASES:

        try:

            summary = run_test(
                test_case
            )

        except Exception as exc:

            summary = {
                "test": test_case["name"],
                "success": False,
                "status": "exception",
                "error": str(exc),
            }

            print()
            print("TEST EXCEPTION")
            print(
                json.dumps(
                    summary,
                    indent=2,
                )
            )

        summaries.append(
            summary
        )

    passed = sum(
        1
        for summary in summaries
        if summary.get("success") is True
    )

    total = len(
        summaries
    )

    print()
    print("=" * 75)
    print("FINAL TEST SUITE RESULT")
    print("=" * 75)

    print(
        json.dumps(
            {
                "passed": passed,
                "total": total,
                "all_passed": passed == total,
                "tests": summaries,
            },
            indent=2,
        )
    )

    print()

    if passed == total:

        print(
            "SUCCESS: All autonomous workflow tests passed."
        )

    else:

        print(
            "WARNING: One or more autonomous workflow tests failed."
        )
