from typing import Any, Dict


class HumanApprovalTool:
    """
    Represents a human-in-the-loop approval gate.

    The autonomous worker should use this whenever a planned
    operation requires explicit authorization.
    """

    name = "request_human_approval"

    def execute(
        self,
        reason: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:

        return {
            "success": True,
            "approval_required": True,
            "status": "pending",
            "reason": reason,
            "context": context,
            "message": (
                "Human approval is required before "
                "this action can continue."
            ),
        }


if __name__ == "__main__":

    tool = HumanApprovalTool()

    result = tool.execute(
        reason="High-value invoice update.",
        context={
            "invoice_id": "ACME-2026-003",
            "amount": 84500,
        },
    )

    print(result)
