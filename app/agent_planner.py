import json
from typing import Any, Dict

from app.llm.groq_client import GroqClient


class TaskPlanner:
    """
    Converts a natural-language user task into a structured
    execution plan for the CentrAlign autonomous worker.
    """

    def __init__(self):
        self.llm = GroqClient()

    def create_plan(self, task: str) -> Dict[str, Any]:
        """
        Ask the LLM to understand the user's objective and
        produce a structured execution plan.
        """

        system_prompt = """
You are the planning component of an autonomous enterprise AI worker.

Your job is to convert a user's natural-language task into a precise,
executable plan.

The worker has access to a small set of tools.

Available tools:

1. search_invoices
   Purpose:
   Search the company's invoice repository.

2. read_invoice
   Purpose:
   Read an invoice and extract relevant information.

3. update_finance_system
   Purpose:
   Create or update an invoice record in the simulated internal
   finance system.

4. verify_invoice
   Purpose:
   Verify that the requested finance-system update actually happened
   correctly.

5. request_human_approval
   Purpose:
   Ask a human for approval when an action is risky, ambiguous,
   or requires authorization.

Rules:

- Understand the user's END GOAL.
- Do not blindly copy the user's wording into steps.
- Break the task into logical executable actions.
- Use only the available tools.
- Include required parameters when they can be inferred.
- Do not invent information that is not available.
- Verification should be included whenever the task changes data.
- Human approval should be included when an action requires authorization.
- Keep the plan as small as reasonably possible.
- Do not execute tools yourself.
- Return ONLY valid JSON.

The JSON must follow exactly this structure:

{
  "goal": "string",
  "requires_human_approval": false,
  "steps": [
    {
      "step": 1,
      "tool": "tool_name",
      "action": "what the tool should accomplish",
      "parameters": {}
    }
  ]
}
"""

        user_prompt = f"""
Create an execution plan for this user task:

{task}
"""

        raw_response = self.llm.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0,
            max_completion_tokens=1200,
            reasoning_effort="low",
        )

        return self._parse_response(raw_response)

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """
        Parse the LLM response into a Python dictionary.
        """

        response = response.strip()

        # Remove accidental markdown code fences.
        if response.startswith("```"):
            lines = response.splitlines()

            if lines and lines[0].startswith("```"):
                lines = lines[1:]

            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            response = "\n".join(lines).strip()

        try:
            plan = json.loads(response)

        except json.JSONDecodeError as exc:
            raise ValueError(
                "The planner returned invalid JSON.\n\n"
                f"Raw response:\n{response}"
            ) from exc

        self._validate_plan(plan)

        return plan

    def _validate_plan(self, plan: Dict[str, Any]) -> None:
        """
        Basic safety and correctness validation before the plan
        reaches the execution layer.
        """

        if not isinstance(plan, dict):
            raise ValueError(
                "Planner output must be a JSON object."
            )

        if "goal" not in plan:
            raise ValueError(
                "Planner output is missing 'goal'."
            )

        if "steps" not in plan:
            raise ValueError(
                "Planner output is missing 'steps'."
            )

        if not isinstance(plan["steps"], list):
            raise ValueError(
                "'steps' must be a list."
            )

        allowed_tools = {
            "search_invoices",
            "read_invoice",
            "update_finance_system",
            "verify_invoice",
            "request_human_approval",
        }

        for step in plan["steps"]:

            if not isinstance(step, dict):
                raise ValueError(
                    "Every plan step must be an object."
                )

            required_fields = {
                "step",
                "tool",
                "action",
                "parameters",
            }

            missing = required_fields - set(step.keys())

            if missing:
                raise ValueError(
                    f"Plan step is missing fields: {missing}"
                )

            if step["tool"] not in allowed_tools:
                raise ValueError(
                    f"Unknown tool selected: {step['tool']}"
                )


if __name__ == "__main__":

    print("=" * 70)
    print("CentrAlign AI - Autonomous Task Planner")
    print("=" * 70)

    planner = TaskPlanner()

    task = (
        "Find the latest invoice from Acme, extract the amount "
        "and due date, enter it into the internal finance system, "
        "and verify that the update was completed correctly."
    )

    print()
    print("USER TASK:")
    print(task)

    print()
    print("Creating autonomous execution plan...")

    plan = planner.create_plan(task)

    print()
    print("=" * 70)
    print("GENERATED PLAN")
    print("=" * 70)

    print(
        json.dumps(
            plan,
            indent=2,
            ensure_ascii=False,
        )
    )

    print()
    print("Planner test completed successfully.")
