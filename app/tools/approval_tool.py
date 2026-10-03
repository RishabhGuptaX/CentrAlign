"""Human-in-the-loop approval tool."""

class ApprovalTool:
    name = "human_approval"

    def request(self, reason: str):
        return {
            "required": True,
            "reason": reason,
        }
