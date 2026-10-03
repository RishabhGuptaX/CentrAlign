import json
import re
import uuid

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


from app.agent_planner import TaskPlanner
from app.tool_router import ToolRouter


class ExecutionEngine:
    """
    CentrAlign autonomous task execution engine.

    Responsibilities:
    - Understand a task through the LLM planner.
    - Execute a dynamic multi-step plan.
    - Resolve references between previous outputs.
    - Normalize LLM parameter variations.
    - Enforce company policy.
    - Pause for human approval when needed.
    - Persist paused execution state.
    - Resume from the exact blocked step.
    - Verify business outcomes independently.
    - Recover from verification mismatches.
    - Return structured evidence for the UI and evaluator.
    """

    STATE_DIRECTORY = ".centralign_state"

    def __init__(self):

        self.planner = TaskPlanner()

        self.router = ToolRouter()

        self.root_dir = (
            Path(__file__)
            .resolve()
            .parent
            .parent
        )

        self.state_dir = (
            self.root_dir
            / self.STATE_DIRECTORY
        )

        self.state_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.run_id = str(
            uuid.uuid4()
        )

        self.execution_log: List[
            Dict[str, Any]
        ] = []

        self.step_outputs: Dict[
            int, Any
        ] = {}

        self.recovery_attempted = False

        self.policy = (
            self.load_policy()
        )

    # ============================================================
    # POLICY
    # ============================================================

    def load_policy(
        self,
    ) -> Dict[str, Any]:

        policy_path = (
            self.root_dir
            / "data"
            / "company_policy.json"
        )

        if not policy_path.exists():

            return {
                "company_name": "Unknown",
                "policies": {},
            }

        try:

            with open(
                policy_path,
                "r",
                encoding="utf-8-sig",
            ) as file:

                return json.load(file)

        except Exception as exc:

            self.log(
                "policy_load_failed",
                {
                    "error": str(exc),
                },
            )

            return {
                "company_name": "Unknown",
                "policies": {},
            }

    # ============================================================
    # LOGGING
    # ============================================================

    def log(
        self,
        event_type: str,
        data: Dict[str, Any],
    ):

        entry = {
            "timestamp": (
                datetime.utcnow()
                .isoformat()
            ),
            "event": event_type,
            "data": data,
        }

        self.execution_log.append(
            entry
        )

        print()
        print(
            f"[{event_type.upper()}]"
        )

        print(
            json.dumps(
                data,
                indent=2,
                default=str,
            )
        )

    # ============================================================
    # GENERIC FIELD SEARCH
    # ============================================================

    def find_field(
        self,
        data: Any,
        field_name: str,
    ) -> Any:

        if isinstance(
            data,
            dict,
        ):

            if field_name in data:

                return data[
                    field_name
                ]

            for value in data.values():

                found = (
                    self.find_field(
                        value,
                        field_name,
                    )
                )

                if found is not None:

                    return found

        elif isinstance(
            data,
            list,
        ):

            for item in data:

                found = (
                    self.find_field(
                        item,
                        field_name,
                    )
                )

                if found is not None:

                    return found

        return None

    # ============================================================
    # STEP OUTPUT
    # ============================================================

    def get_step_output(
        self,
        step_number: int,
    ) -> Any:

        if (
            step_number
            not in self.step_outputs
        ):

            raise ValueError(
                f"Output from step "
                f"{step_number} is not available."
            )

        return self.step_outputs[
            step_number
        ]

    # ============================================================
    # REFERENCE RESOLUTION
    # ============================================================

    def resolve_reference(
        self,
        value: Any,
    ) -> Any:

        if not isinstance(
            value,
            str,
        ):

            return value

        # --------------------------------------------------------
        # Exact step reference
        # output_of_step_1
        # --------------------------------------------------------

        exact_match = re.fullmatch(
            r"output_of_step_(\d+)",
            value,
        )

        if exact_match:

            step_number = int(
                exact_match.group(1)
            )

            output = (
                self.get_step_output(
                    step_number
                )
            )

            if (
                isinstance(
                    output,
                    dict,
                )
                and isinstance(
                    output.get(
                        "results"
                    ),
                    list,
                )
                and output[
                    "results"
                ]
            ):

                return output[
                    "results"
                ][0]

            return output

        # --------------------------------------------------------
        # Nested step reference
        # output_of_step_1.invoice_id
        # --------------------------------------------------------

        nested_match = re.fullmatch(
            r"output_of_step_(\d+)\.(.+)",
            value,
        )

        if nested_match:

            step_number = int(
                nested_match.group(1)
            )

            field_path = (
                nested_match.group(2)
            )

            output = (
                self.get_step_output(
                    step_number
                )
            )

            # ------------------------------------------------

            # Semantic planner alias.

            #

            # Some LLM plans refer to the payload returned

            # by read_invoice as `details`, while the actual

            # reader exposes it as `extracted` or `invoice`.

            # ------------------------------------------------

            if field_path == "details" and isinstance(output, dict):

                extracted = output.get("extracted")

                if isinstance(extracted, dict):

                    return extracted

                invoice = output.get("invoice")

                if isinstance(invoice, dict):

                    return invoice


            current = output

            try:

                for part in (
                    field_path.split(".")
                ):

                    if isinstance(
                        current,
                        dict,
                    ):

                        current = current[
                            part
                        ]

                    elif isinstance(
                        current,
                        list,
                    ):

                        current = current[
                            int(part)
                        ]

                    else:

                        raise KeyError(
                            part
                        )

                return current

            except (
                KeyError,
                IndexError,
                TypeError,
                ValueError,
            ):

                field_name = (
                    field_path
                    .split(".")[-1]
                )

                found = (
                    self.find_field(
                        output,
                        field_name,
                    )
                )

                if found is not None:

                    return found

                raise ValueError(
                    f"Field '{field_path}' "
                    f"was not found in "
                    f"step {step_number} output."
                )

        return value

    # ============================================================
    # RESOLVE PARAMETERS
    # ============================================================

    def resolve_parameters(
        self,
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:

        resolved = {}

        for key, value in (
            parameters.items()
        ):

            resolved[key] = (
                self.resolve_reference(
                    value
                )
            )

        return resolved

    # ============================================================
    # FIND INVOICE FILE BY ID
    # ============================================================

    def find_invoice_file(
        self,
        invoice_id: str,
    ) -> Optional[str]:

        invoices_dir = (
            self.root_dir
            / "data"
            / "invoices"
        )

        if not invoices_dir.exists():

            return None

        target = str(
            invoice_id
        ).strip().lower()

        for file_path in (
            invoices_dir.glob("*.json")
        ):

            try:

                with open(
                    file_path,
                    "r",
                    encoding="utf-8-sig",
                ) as file:

                    data = json.load(
                        file
                    )

                candidate = str(
                    data.get(
                        "invoice_id",
                        "",
                    )
                ).strip().lower()

                if (
                    candidate == target
                ):

                    return str(
                        file_path
                        .relative_to(
                            self.root_dir
                        )
                    )

            except Exception:

                continue

        return None

    # ============================================================
    # NORMALIZE PARAMETERS
    # ============================================================

    def normalize_parameters(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:

        params = dict(parameters)

        # ========================================================
        # Helper: retrieve the latest search result from memory.
        # ========================================================

        def latest_search_result():

            for output in reversed(
                list(
                    self.step_outputs.values()
                )
            ):

                if not isinstance(
                    output,
                    dict,
                ):
                    continue

                results = output.get(
                    "results"
                )

                if (
                    isinstance(
                        results,
                        list,
                    )
                    and results
                    and isinstance(
                        results[0],
                        dict,
                    )
                ):

                    return results[0]

            return None

        # ========================================================
        # Helper: retrieve the latest invoice payload from memory.
        # ========================================================

        def latest_invoice():

            for output in reversed(
                list(
                    self.step_outputs.values()
                )
            ):

                if not isinstance(
                    output,
                    dict,
                ):
                    continue

                extracted = output.get(
                    "extracted"
                )

                if isinstance(
                    extracted,
                    dict,
                ):

                    return extracted

                invoice = output.get(
                    "invoice"
                )

                if isinstance(
                    invoice,
                    dict,
                ):

                    return invoice

            return {}

        # ========================================================
        # SEARCH
        # ========================================================

        if tool_name == "search_invoices":

            aliases = {
                "vendor": "company",
                "supplier": "company",
                "customer": "company",
            }

            for source, target in aliases.items():

                if (
                    target not in params
                    and source in params
                ):

                    params[target] = params.pop(
                        source
                    )

            # Search tool only needs the company.
            for key in [
                "sort_by",
                "order",
                "sort_order",
                "direction",
                "limit",
                "count",
                "max_results",
            ]:

                params.pop(
                    key,
                    None
                )

        # ========================================================
        # READ INVOICE
        # ========================================================

        elif tool_name == "read_invoice":

            reference = params.get(
                "invoice_id"
            )

            # ----------------------------------------------------
            # Direct result object.
            # ----------------------------------------------------

            if isinstance(
                reference,
                dict,
            ):

                if reference.get(
                    "file"
                ):

                    params["file"] = reference[
                        "file"
                    ]

                elif reference.get(
                    "invoice_id"
                ):

                    invoice_file = (
                        self.find_invoice_file(
                            reference[
                                "invoice_id"
                            ]
                        )
                    )

                    if invoice_file:
                        params["file"] = invoice_file

            # ----------------------------------------------------
            # Symbolic alias:
            # latest_acme_invoice_id
            # latest_invoice_id
            # etc.
            # ----------------------------------------------------

            if (
                "file" not in params
                and isinstance(
                    reference,
                    str,
                )
                and (
                    reference.lower().startswith(
                        "latest_"
                    )
                    or reference.lower()
                    in {
                        "latest_invoice_id",
                        "most_recent_invoice_id",
                    }
                )
            ):

                latest = latest_search_result()

                if latest and latest.get(
                    "file"
                ):

                    params["file"] = latest[
                        "file"
                    ]

            # ----------------------------------------------------
            # Generic memory fallback.
            # ----------------------------------------------------

            if "file" not in params:

                latest = latest_search_result()

                if latest and latest.get(
                    "file"
                ):

                    params["file"] = latest[
                        "file"
                    ]

            # ----------------------------------------------------
            # read_invoice accepts only file.
            # ----------------------------------------------------

            params.pop(
                "invoice_id",
                None
            )

        # ========================================================
        # FINANCE UPDATE
        # ========================================================

        elif tool_name == "update_finance_system":

            invoice = latest_invoice()

            reference = params.get(
                "invoice_id"
            )

            if isinstance(
                reference,
                dict,
            ):

                invoice_id = reference.get(
                    "invoice_id"
                )

                if invoice_id:

                    params["invoice_id"] = (
                        invoice_id
                    )

            # Resolve planner aliases.
            invoice_id_value = params.get(
                "invoice_id"
            )

            if (
                not invoice_id_value
                or (
                    isinstance(
                        invoice_id_value,
                        str,
                    )
                    and invoice_id_value.lower()
                    .startswith(
                        "latest_"
                    )
                )
            ):

                if invoice.get(
                    "invoice_id"
                ):

                    params["invoice_id"] = (
                        invoice[
                            "invoice_id"
                        ]
                    )

            amount_value = params.get(
                "amount"
            )

            if (
                amount_value is None
                or (
                    isinstance(
                        amount_value,
                        str,
                    )
                    and (
                        amount_value.lower()
                        .startswith(
                            "extracted_"
                        )
                        or amount_value.lower()
                        in {
                            "invoice_amount",
                            "latest_invoice_amount",
                        }
                    )
                )
            ):

                if invoice.get(
                    "amount"
                ) is not None:

                    params["amount"] = (
                        invoice[
                            "amount"
                        ]
                    )

            due_date_value = params.get(
                "due_date"
            )

            if (
                not due_date_value
                or (
                    isinstance(
                        due_date_value,
                        str,
                    )
                    and (
                        due_date_value.lower()
                        .startswith(
                            "extracted_"
                        )
                        or due_date_value.lower()
                        in {
                            "invoice_due_date",
                            "latest_invoice_due_date",
                        }
                    )
                )
            ):

                if invoice.get(
                    "due_date"
                ):

                    params["due_date"] = (
                        invoice[
                            "due_date"
                        ]
                    )

            # Finance tool schema.
            for key in [
                "vendor",
                "company",
                "supplier",
                "customer",
            ]:

                params.pop(
                    key,
                    None
                )

        # ========================================================
        # VERIFY INVOICE
        # ========================================================

        elif tool_name == "verify_invoice":

            invoice = latest_invoice()

            # ----------------------------------------------------
            # Resolve invoice id.
            # ----------------------------------------------------

            reference = params.get(
                "invoice_id"
            )

            if isinstance(
                reference,
                dict,
            ):

                candidate_id = reference.get(
                    "invoice_id"
                )

                if candidate_id:
                    params["invoice_id"] = (
                        candidate_id
                    )

            invoice_id_value = params.get(
                "invoice_id"
            )

            if (
                not invoice_id_value
                or (
                    isinstance(
                        invoice_id_value,
                        str,
                    )
                    and (
                        invoice_id_value.lower()
                        .startswith(
                            "latest_"
                        )
                        or invoice_id_value.lower()
                        in {
                            "latest_invoice_id",
                            "most_recent_invoice_id",
                        }
                    )
                )
            ):

                if invoice.get(
                    "invoice_id"
                ):

                    params["invoice_id"] = (
                        invoice[
                            "invoice_id"
                        ]
                    )

            # ----------------------------------------------------
            # expected_amount
            # ----------------------------------------------------

            expected_amount = params.get(
                "expected_amount"
            )

            source_amount = params.get(
                "amount"
            )

            if (
                expected_amount is None
                or (
                    isinstance(
                        expected_amount,
                        str,
                    )
                    and (
                        expected_amount.lower()
                        .startswith(
                            "extracted_"
                        )
                        or expected_amount.lower()
                        in {
                            "invoice_amount",
                            "latest_invoice_amount",
                        }
                    )
                )
            ):

                if (
                    source_amount is not None
                    and not (
                        isinstance(
                            source_amount,
                            str,
                        )
                        and source_amount.lower()
                        .startswith(
                            "extracted_"
                        )
                    )
                ):

                    params["expected_amount"] = (
                        source_amount
                    )

                elif invoice.get(
                    "amount"
                ) is not None:

                    params["expected_amount"] = (
                        invoice[
                            "amount"
                        ]
                    )

            # ----------------------------------------------------
            # expected_due_date
            # ----------------------------------------------------

            expected_due_date = params.get(
                "expected_due_date"
            )

            source_due_date = params.get(
                "due_date"
            )

            if (
                not expected_due_date
                or (
                    isinstance(
                        expected_due_date,
                        str,
                    )
                    and (
                        expected_due_date.lower()
                        .startswith(
                            "extracted_"
                        )
                        or expected_due_date.lower()
                        in {
                            "invoice_due_date",
                            "latest_invoice_due_date",
                        }
                    )
                )
            ):

                if (
                    source_due_date
                    and not (
                        isinstance(
                            source_due_date,
                            str,
                        )
                        and source_due_date.lower()
                        .startswith(
                            "extracted_"
                        )
                    )
                ):

                    params["expected_due_date"] = (
                        source_due_date
                    )

                elif invoice.get(
                    "due_date"
                ):

                    params["expected_due_date"] = (
                        invoice[
                            "due_date"
                        ]
                    )

            # ----------------------------------------------------
            # The verification tool accepts only:
            #
            # invoice_id
            # expected_amount
            # expected_due_date
            #
            # Remove every planner-only synonym.
            # ----------------------------------------------------

            for key in [
                "amount",
                "due_date",
                "invoice_number",
                "number",
                "date",
                "line_items",
                "details",
                "expected_details",
                "extracted_invoice_number",
                "extracted_date",
                "extracted_amount",
                "extracted_due_date",
                "extracted_line_items",
                "vendor",
                "company",
                "supplier",
                "customer",
            ]:

                params.pop(
                    key,
                    None
                )

        return params

    def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:

        try:

            return self.router.execute(
                tool_name,
                parameters,
            )

        except Exception as exc:

            return {
                "success": False,
                "error": str(exc),
            }

    # ============================================================
    # STORE STEP OUTPUT
    # ============================================================

    def save_step_output(
        self,
        step_number: int,
        result: Dict[str, Any],
    ):

        actual_result = result.get(
            "result",
            result,
        )

        self.step_outputs[
            step_number
        ] = actual_result

    # ============================================================
    # VERIFICATION
    # ============================================================

    def verification_passed(
        self,
        result: Dict[str, Any],
    ) -> bool:

        # First ensure the verifier itself ran.
        if not result.get(
            "success",
            False,
        ):

            return False

        verification_result = (
            result.get(
                "result",
                result,
            )
        )

        if not isinstance(
            verification_result,
            dict,
        ):

            return False

        return (
            verification_result.get(
                "verified",
                False,
            )
            is True
        )

    # ============================================================
    # POLICY
    # ============================================================

    def requires_approval(
        self,
        amount: float,
    ) -> bool:

        policies = self.policy.get(
            "policies",
            {},
        )

        if not policies.get(
            "high_value_updates_require_human_approval",
            False,
        ):

            return False

        threshold = float(
            policies.get(
                "high_value_threshold",
                float("inf"),
            )
        )

        return float(amount) >= threshold

    # ============================================================
    # REQUEST APPROVAL
    # ============================================================

    def request_approval(
        self,
        invoice_id: str,
        amount: float,
        due_date: str,
    ) -> Dict[str, Any]:

        policies = (
            self.policy.get(
                "policies",
                {},
            )
        )

        threshold = (
            policies.get(
                "high_value_threshold"
            )
        )

        reason = (
            "The invoice amount meets or exceeds "
            "the company's high-value approval threshold."
        )

        approval_result = (
            self.execute_tool(
                "request_human_approval",
                {
                    "reason": reason,
                    "context": {
                        "invoice_id": invoice_id,
                        "amount": amount,
                        "due_date": due_date,
                        "threshold": threshold,
                    },
                },
            )
        )

        self.log(
            "approval_requested",
            approval_result,
        )

        return approval_result

    # ============================================================
    # EXECUTE ONE STEP
    # ============================================================

    def is_retryable_failure(
        self,
        tool_name: str,
        result: Dict[str, Any],
    ) -> bool:
        """
        Decide whether a failed tool call is safe to retry once.

        Only clearly transient failures are retried.
        Semantic/business failures are allowed to stop normally.
        """

        if tool_name == "verify_invoice":
            return False

        error_text = str(
            result.get("error", "")
        ).lower()

        transient_signals = [
            "timeout",
            "timed out",
            "temporarily unavailable",
            "temporary failure",
            "connection reset",
            "connection refused",
            "network error",
            "rate limit",
            "too many requests",
            "service unavailable",
            "bad gateway",
            "gateway timeout",
            "http 500",
            "http 502",
            "http 503",
            "http 504",
        ]

        return any(
            signal in error_text
            for signal in transient_signals
        )


    def execute_step(
        self,
        step: Dict[str, Any],
        simulate_failure: bool = False,
    ) -> Dict[str, Any]:

        step_number = step.get(
            "step"
        )

        tool_name = step.get(
            "tool"
        )

        raw_parameters = step.get(
            "parameters",
            {},
        )

        self.log(
            "step_started",
            {
                "step": step_number,
                "tool": tool_name,
                "action": step.get(
                    "action"
                ),
                "raw_parameters": raw_parameters,
            },
        )

        # --------------------------------------------------------
        # Resolve references once.
        #
        # Reference-resolution failures are semantic failures,
        # not transient tool failures, so do not retry them.
        # --------------------------------------------------------

        try:

            resolved_parameters = (
                self.resolve_parameters(
                    raw_parameters
                )
            )

        except Exception as exc:

            self.log(
                "parameter_resolution_failed",
                {
                    "step": step_number,
                    "tool": tool_name,
                    "error": str(exc),
                },
            )

            return {
                "success": False,
                "error": str(exc),
            }

        normalized_parameters = (
            self.normalize_parameters(
                tool_name,
                resolved_parameters,
            )
        )

        # --------------------------------------------------------
        # Maximum of one retry.
        #
        # We intentionally avoid blind repeated execution because
        # some tools may perform writes.
        # --------------------------------------------------------

        max_attempts = 2

        for attempt in range(
            1,
            max_attempts + 1,
        ):

            attempt_parameters = dict(
                normalized_parameters
            )

            # ----------------------------------------------------
            # Inject the existing intentional finance failure only
            # into the first attempt.
            # ----------------------------------------------------

            if (
                simulate_failure
                and tool_name
                == "update_finance_system"
                and not self.recovery_attempted
                and attempt == 1
            ):

                attempt_parameters[
                    "simulate_failure"
                ] = True

            self.log(
                "parameters_resolved",
                {
                    "step": step_number,
                    "tool": tool_name,
                    "attempt": attempt,
                    "parameters": attempt_parameters,
                },
            )

            result = self.execute_tool(
                tool_name,
                attempt_parameters,
            )

            # ----------------------------------------------------
            # Success.
            # ----------------------------------------------------

            if result.get(
                "success",
                False,
            ):

                self.save_step_output(
                    step_number,
                    result,
                )

                self.log(
                    "step_completed",
                    {
                        "step": step_number,
                        "tool": tool_name,
                        "attempt": attempt,
                        "result": result.get(
                            "result",
                            result,
                        ),
                    },
                )

                if attempt > 1:

                    self.log(
                        "retry_succeeded",
                        {
                            "step": step_number,
                            "tool": tool_name,
                            "attempt": attempt,
                            "message": (
                                "The worker recovered from "
                                "a transient tool failure."
                            ),
                        },
                    )

                return result

            # ----------------------------------------------------
            # Failure.
            # ----------------------------------------------------

            error_text = result.get(
                "error",
                result,
            )

            self.log(
                "step_failed",
                {
                    "step": step_number,
                    "tool": tool_name,
                    "attempt": attempt,
                    "error": error_text,
                },
            )

            # ----------------------------------------------------
            # Retry only when:
            #
            # 1. this was the first attempt,
            # 2. the tool failure is clearly transient,
            # 3. the tool is not the verifier.
            #
            # This prevents dangerous blind retries for semantic
            # failures or verification mismatches.
            # ----------------------------------------------------

            if (
                attempt < max_attempts
                and self.is_retryable_failure(
                    tool_name,
                    result,
                )
            ):

                self.log(
                    "retry_started",
                    {
                        "step": step_number,
                        "tool": tool_name,
                        "attempt": attempt,
                        "next_attempt": attempt + 1,
                        "reason": str(
                            error_text
                        ),
                    },
                )

                continue

            return result

        return {
            "success": False,
            "error": "Tool execution failed after retry.",
        }

    def recover_from_verification_failure(
        self,
    ) -> bool:

        if self.recovery_attempted:

            return False

        self.recovery_attempted = True

        self.log(
            "recovery_started",
            {
                "reason": (
                    "Independent verification detected "
                    "that the requested business outcome "
                    "was incorrect."
                ),
            },
        )

        try:

            invoice_output = (
                self.get_step_output(
                    2
                )
            )

            invoice = (
                invoice_output.get(
                    "extracted",
                    invoice_output.get(
                        "invoice",
                        {},
                    ),
                )
            )

            invoice_id = (
                invoice.get(
                    "invoice_id"
                )
            )

            amount = (
                invoice.get(
                    "amount"
                )
            )

            due_date = (
                invoice.get(
                    "due_date"
                )
            )

            if not all(
                [
                    invoice_id,
                    amount is not None,
                    due_date,
                ]
            ):

                raise ValueError(
                    "Recovery could not obtain "
                    "trusted invoice values."
                )

            self.log(
                "recovery_action",
                {
                    "action": (
                        "Use trusted invoice data "
                        "to repair the finance record."
                    ),
                    "invoice_id": invoice_id,
                    "amount": amount,
                    "due_date": due_date,
                },
            )

            repair_result = (
                self.execute_tool(
                    "update_finance_system",
                    {
                        "invoice_id": invoice_id,
                        "amount": amount,
                        "due_date": due_date,
                        "simulate_failure": False,
                    },
                )
            )

            if not repair_result.get(
                "success",
                False,
            ):

                self.log(
                    "recovery_failed",
                    {
                        "stage": "repair",
                        "result": repair_result,
                    },
                )

                return False

            self.log(
                "recovery_update_completed",
                repair_result,
            )

            verification_result = (
                self.execute_tool(
                    "verify_invoice",
                    {
                        "invoice_id": invoice_id,
                        "expected_amount": amount,
                        "expected_due_date": due_date,
                    },
                )
            )

            self.log(
                "recovery_verification",
                verification_result,
            )

            if self.verification_passed(
                verification_result
            ):

                self.log(
                    "recovery_succeeded",
                    {
                        "invoice_id": invoice_id,
                        "message": (
                            "The worker detected an incorrect "
                            "business state, repaired the record, "
                            "and confirmed the corrected state."
                        ),
                    },
                )

                return True

            self.log(
                "recovery_failed",
                {
                    "stage": (
                        "post_repair_verification"
                    ),
                    "result": verification_result,
                },
            )

            return False

        except Exception as exc:

            self.log(
                "recovery_failed",
                {
                    "error": str(exc),
                },
            )

            return False

    # ============================================================
    # PAUSED STATE
    # ============================================================

    def _pause_file_for_run(
        self,
        run_id: Optional[str] = None,
    ) -> Path:

        target_run_id = (
            run_id
            or self.run_id
        )

        return (
            self.state_dir
            / f"pending_{target_run_id}.json"
        )

    def _save_pause_state(
        self,
        task: str,
        plan: Dict[str, Any],
        step_results: List[Dict[str, Any]],
        next_step_index: int,
        simulate_failure: bool,
        pending_invoice_id: str,
        pending_amount: float,
        pending_due_date: str,
    ) -> Path:

        state = {
            "version": 1,
            "run_id": self.run_id,
            "task": task,
            "plan": plan,
            "step_results": step_results,
            "step_outputs": {
                str(key): value
                for key, value
                in self.step_outputs.items()
            },
            "execution_log": self.execution_log,
            "next_step_index": (
                next_step_index
            ),
            "simulate_failure": (
                simulate_failure
            ),
            "recovery_attempted": (
                self.recovery_attempted
            ),
            "pending_invoice_id": (
                pending_invoice_id
            ),
            "pending_amount": (
                pending_amount
            ),
            "pending_due_date": (
                pending_due_date
            ),
            "saved_at": (
                datetime.utcnow()
                .isoformat()
            ),
        }

        pause_file = (
            self._pause_file_for_run()
        )

        with open(
            pause_file,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                state,
                file,
                indent=2,
                ensure_ascii=False,
                default=str,
            )

        self.log(
            "execution_state_persisted",
            {
                "run_id": self.run_id,
                "next_step_index": (
                    next_step_index
                ),
                "message": (
                    "Paused execution state "
                    "was persisted for continuation."
                ),
            },
        )

        # Persist the newest log event as well.

        state[
            "execution_log"
        ] = self.execution_log

        with open(
            pause_file,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                state,
                file,
                indent=2,
                ensure_ascii=False,
                default=str,
            )

        return pause_file

    def _load_pause_state(
        self,
        pause_file: Path,
    ) -> Optional[
        Dict[str, Any]
    ]:

        try:

            with open(
                pause_file,
                "r",
                encoding="utf-8-sig",
            ) as file:

                state = json.load(
                    file
                )

            if not isinstance(
                state,
                dict,
            ):

                return None

            state[
                "_pause_file"
            ] = str(
                pause_file
            )

            return state

        except Exception as exc:

            print(
                "Unable to load paused state:",
                exc,
            )

            return None

    def _find_latest_paused_state(
        self,
        task: str,
    ) -> Optional[
        Dict[str, Any]
    ]:

        files = list(
            self.state_dir.glob(
                "pending_*.json"
            )
        )

        if not files:

            return None

        target_task = (
            task.strip().lower()
        )

        matches = []

        for pause_file in files:

            state = (
                self._load_pause_state(
                    pause_file
                )
            )

            if not state:

                continue

            saved_task = (
                str(
                    state.get(
                        "task",
                        "",
                    )
                )
                .strip()
                .lower()
            )

            if (
                saved_task
                == target_task
            ):

                try:

                    modified = (
                        pause_file.stat()
                        .st_mtime
                    )

                except Exception:

                    modified = 0

                matches.append(
                    (
                        modified,
                        state,
                    )
                )

        if not matches:

            return None

        matches.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        return matches[0][1]

    def _restore_pause_state(
        self,
        state: Dict[str, Any],
    ):

        self.run_id = str(
            state.get(
                "run_id",
                self.run_id,
            )
        )

        raw_outputs = (
            state.get(
                "step_outputs",
                {},
            )
        )

        self.step_outputs = {}

        if isinstance(
            raw_outputs,
            dict,
        ):

            for key, value in (
                raw_outputs.items()
            ):

                try:

                    numeric_key = int(
                        key
                    )

                except (
                    TypeError,
                    ValueError,
                ):

                    continue

                self.step_outputs[
                    numeric_key
                ] = value

        self.execution_log = list(
            state.get(
                "execution_log",
                [],
            )
        )

        self.recovery_attempted = bool(
            state.get(
                "recovery_attempted",
                False,
            )
        )

    def _delete_pause_state(
        self,
        state: Optional[
            Dict[str, Any]
        ] = None,
    ):

        pause_file = None

        if isinstance(
            state,
            dict,
        ):

            pause_file = state.get(
                "_pause_file"
            )

        if pause_file:

            path = Path(
                pause_file
            )

        else:

            path = (
                self._pause_file_for_run()
            )

        try:

            if path.exists():

                path.unlink()

        except Exception as exc:

            self.log(
                "pause_state_cleanup_failed",
                {
                    "error": str(exc),
                    "file": str(path),
                },
            )

    # ============================================================
    # PLAN EXECUTION LOOP
    # ============================================================

    def _execute_plan(
        self,
        task: str,
        plan: Dict[str, Any],
        step_results: List[
            Dict[str, Any]
        ],
        start_step_index: int,
        simulate_failure: bool,
        approval_granted: bool,
        resumed: bool = False,
        previous_pause_state: Optional[
            Dict[str, Any]
        ] = None,
    ) -> Dict[str, Any]:

        steps = plan.get(
            "steps",
            [],
        )

        if not isinstance(
            steps,
            list,
        ):

            steps = []

        # --------------------------------------------------------
        # Resume marker
        # --------------------------------------------------------

        if (
            resumed
            and approval_granted
        ):

            pending_invoice_id = (
                previous_pause_state.get(
                    "pending_invoice_id"
                )
                if previous_pause_state
                else None
            )

            pending_amount = (
                previous_pause_state.get(
                    "pending_amount"
                )
                if previous_pause_state
                else None
            )

            self.log(
                "approval_granted",
                {
                    "invoice_id": (
                        pending_invoice_id
                    ),
                    "amount": (
                        pending_amount
                    ),
                    "message": (
                        "Human approval was granted. "
                        "The worker is resuming "
                        "the existing paused run."
                    ),
                },
            )

            self.log(
                "execution_resumed",
                {
                    "run_id": self.run_id,
                    "resume_from_step_index": (
                        start_step_index
                    ),
                    "message": (
                        "Continuing from the "
                        "previously blocked action "
                        "without recreating the plan."
                    ),
                },
            )

        # --------------------------------------------------------
        # Execute remaining steps
        # --------------------------------------------------------

        for plan_index in range(
            start_step_index,
            len(steps),
        ):

            step = steps[
                plan_index
            ]

            step_number = step.get(
                "step"
            )

            tool_name = step.get(
                "tool"
            )

            # ====================================================
            # POLICY GATE
            # ====================================================

            if (
                tool_name
                == "update_finance_system"
            ):

                try:

                    invoice_output = (
                        self.get_step_output(
                            2
                        )
                    )

                    invoice = (
                        invoice_output.get(
                            "extracted",
                            invoice_output.get(
                                "invoice",
                                {},
                            ),
                        )
                    )

                    invoice_id = (
                        invoice.get(
                            "invoice_id"
                        )
                    )

                    amount = float(
                        invoice.get(
                            "amount"
                        )
                    )

                    due_date = (
                        invoice.get(
                            "due_date"
                        )
                    )

                    if self.requires_approval(
                        amount
                    ):

                        threshold = (
                            self.policy
                            .get(
                                "policies",
                                {},
                            )
                            .get(
                                "high_value_threshold"
                            )
                        )

                        self.log(
                            "policy_evaluation",
                            {
                                "invoice_id": (
                                    invoice_id
                                ),
                                "amount": amount,
                                "threshold": (
                                    threshold
                                ),
                                "approval_required": (
                                    True
                                ),
                            },
                        )

                        if not approval_granted:

                            self.request_approval(
                                invoice_id=(
                                    invoice_id
                                ),
                                amount=amount,
                                due_date=(
                                    due_date
                                ),
                            )

                            self.log(
                                "execution_paused",
                                {
                                    "reason": (
                                        "Human approval is "
                                        "required before "
                                        "the finance update."
                                    ),
                                    "invoice_id": (
                                        invoice_id
                                    ),
                                    "amount": amount,
                                    "next_step": (
                                        step_number
                                    ),
                                },
                            )

                            self._save_pause_state(
                                task=task,
                                plan=plan,
                                step_results=(
                                    step_results
                                ),
                                next_step_index=(
                                    plan_index
                                ),
                                simulate_failure=(
                                    simulate_failure
                                ),
                                pending_invoice_id=(
                                    invoice_id
                                ),
                                pending_amount=(
                                    amount
                                ),
                                pending_due_date=(
                                    due_date
                                ),
                            )

                            return {
                                "success": False,
                                "run_id": (
                                    self.run_id
                                ),
                                "status": (
                                    "awaiting_human_approval"
                                ),
                                "goal": plan.get(
                                    "goal"
                                ),
                                "plan": plan,
                                "invoice_id": (
                                    invoice_id
                                ),
                                "amount": amount,
                                "threshold": (
                                    threshold
                                ),
                                "approval_required": (
                                    True
                                ),
                                "resume_available": (
                                    True
                                ),
                                "resume_from_step": (
                                    step_number
                                ),
                                "step_results": (
                                    step_results
                                ),
                                "evidence": (
                                    self.execution_log
                                ),
                            }

                        # ------------------------------------------------
                        # Approval already granted.
                        # Do not pause and do not rerun earlier steps.
                        # ------------------------------------------------

                        else:

                            if not resumed:

                                self.log(
                                    "approval_granted",
                                    {
                                        "invoice_id": (
                                            invoice_id
                                        ),
                                        "amount": amount,
                                        "message": (
                                            "Human approval "
                                            "was granted. "
                                            "The worker may continue."
                                        ),
                                    },
                                )

                except Exception as exc:

                    self.log(
                        "policy_evaluation_failed",
                        {
                            "error": str(exc),
                        },
                    )

                    return {
                        "success": False,
                        "run_id": (
                            self.run_id
                        ),
                        "status": (
                            "policy_evaluation_failed"
                        ),
                        "error": str(exc),
                        "step_results": (
                            step_results
                        ),
                        "evidence": (
                            self.execution_log
                        ),
                    }

            # ====================================================
            # EXECUTE STEP
            # ====================================================

            result = self.execute_step(
                step,
                simulate_failure=(
                    simulate_failure
                ),
            )

            step_results.append(
                {
                    "step": step_number,
                    "tool": tool_name,
                    "result": result,
                }
            )

            # ====================================================
            # VERIFICATION
            # ====================================================

            if (
                tool_name
                == "verify_invoice"
            ):

                # Important:
                #
                # If the verification TOOL itself failed,
                # this is not a business verification mismatch.
                #
                # Do NOT invoke recovery in that situation.

                if not result.get(
                    "success",
                    False,
                ):

                    self.log(
                        "verification_tool_failed",
                        {
                            "step": (
                                step_number
                            ),
                            "error": (
                                result.get(
                                    "error",
                                    result,
                                )
                            ),
                            "message": (
                                "Verification could not "
                                "be executed, so recovery "
                                "was not attempted."
                            ),
                        },
                    )

                    self.log(
                        "execution_stopped",
                        {
                            "failed_step": (
                                step_number
                            ),
                            "reason": (
                                "Verification tool failed "
                                "to execute."
                            ),
                        },
                    )

                    return {
                        "success": False,
                        "run_id": (
                            self.run_id
                        ),
                        "status": (
                            "verification_tool_failed"
                        ),
                        "failed_step": (
                            step_number
                        ),
                        "step_results": (
                            step_results
                        ),
                        "evidence": (
                            self.execution_log
                        ),
                    }

                # ------------------------------------------------
                # Tool executed successfully.
                # Now check business outcome.
                # ------------------------------------------------

                if self.verification_passed(
                    result
                ):

                    self.log(
                        "verification_passed",
                        {
                            "step": (
                                step_number
                            ),
                            "message": (
                                "Independent verification "
                                "confirmed the requested "
                                "business outcome."
                            ),
                        },
                    )

                    continue

                # ------------------------------------------------
                # Actual business mismatch.
                # Recovery is appropriate here.
                # ------------------------------------------------

                self.log(
                    "verification_failed",
                    {
                        "step": (
                            step_number
                        ),
                        "message": (
                            "Verification executed "
                            "successfully, but the requested "
                            "business outcome was not satisfied."
                        ),
                    },
                )

                recovered = (
                    self.recover_from_verification_failure()
                )

                if recovered:

                    step_results.append(
                        {
                            "step": "recovery",
                            "tool": (
                                "update_finance_system"
                            ),
                            "result": {
                                "success": True,
                                "recovered": True,
                            },
                        }
                    )

                    step_results.append(
                        {
                            "step": (
                                "recovery_verify"
                            ),
                            "tool": (
                                "verify_invoice"
                            ),
                            "result": {
                                "success": True,
                                "verified": True,
                                "recovered": True,
                            },
                        }
                    )

                    break

                return {
                    "success": False,
                    "run_id": (
                        self.run_id
                    ),
                    "status": (
                        "verification_failed"
                    ),
                    "failed_step": (
                        step_number
                    ),
                    "step_results": (
                        step_results
                    ),
                    "evidence": (
                        self.execution_log
                    ),
                }

            # ====================================================
            # ORDINARY TOOL FAILURE
            # ====================================================

            if not result.get(
                "success",
                False,
            ):

                self.log(
                    "execution_stopped",
                    {
                        "failed_step": (
                            step_number
                        ),
                        "reason": (
                            "Tool execution failed "
                            "and no safe recovery "
                            "was available."
                        ),
                    },
                )

                return {
                    "success": False,
                    "run_id": (
                        self.run_id
                    ),
                    "status": (
                        "execution_failed"
                    ),
                    "failed_step": (
                        step_number
                    ),
                    "step_results": (
                        step_results
                    ),
                    "evidence": (
                        self.execution_log
                    ),
                }

        # ========================================================
        # FINAL SUCCESS
        # ========================================================

        self.log(
            "task_completed",
            {
                "goal": plan.get(
                    "goal"
                ),
                "steps_completed": len(
                    step_results
                ),
                "recovery_used": (
                    self.recovery_attempted
                ),
                "approval_used": (
                    approval_granted
                ),
                "resumed_from_pause": (
                    resumed
                ),
            },
        )

        result = {
            "success": True,
            "run_id": self.run_id,
            "status": "completed",
            "goal": plan.get(
                "goal"
            ),
            "recovery_used": (
                self.recovery_attempted
            ),
            "approval_used": (
                approval_granted
            ),
            "resumed_from_pause": (
                resumed
            ),
            "step_results": (
                step_results
            ),
            "evidence": (
                self.execution_log
            ),
        }

        if resumed:

            self._delete_pause_state(
                previous_pause_state
            )

            self.log(
                "paused_state_cleared",
                {
                    "run_id": (
                        self.run_id
                    ),
                    "message": (
                        "Completed run no longer "
                        "requires a resumable checkpoint."
                    ),
                },
            )

            result[
                "evidence"
            ] = self.execution_log

        return result

    # ============================================================
    # MAIN ENTRY POINT
    # ============================================================

    def analyze_task_clarity(
        self,
        task: str,
    ) -> dict:
        """
        Lightweight safety gate before planning.

        The planner may decide HOW to complete a clear request,
        but it should not invent missing user intent.
        """
        normalized = task.strip().lower()

        if not normalized:
            return {
                "clear": False,
                "reason": "empty_task",
                "question": "What would you like me to accomplish?",
                "options": [],
            }

        invoice_request = (
            "invoice" in normalized
            or "invoices" in normalized
        )

        if not invoice_request:
            return {
                "clear": True,
                "reason": None,
                "question": None,
                "options": [],
            }

        known_companies = [
            "acme",
            "globex",
            "initech",
        ]

        company_present = any(
            company in normalized
            for company in known_companies
        )

        invoice_id_present = bool(
            __import__("re").search(
                r"\b[A-Z]{3,12}-\d{4}-\d{3}\b",
                task,
                flags=__import__("re").IGNORECASE,
            )
        )

        if not company_present and not invoice_id_present:
            return {
                "clear": False,
                "reason": "missing_company",
                "question": "Which company should I work with?",
                "options": [
                    "Acme",
                    "Globex",
                    "Initech",
                ],
            }

        intent_signals = [
            "find",
            "search",
            "latest",
            "extract",
            "amount",
            "due date",
            "due_date",
            "read",
            "enter",
            "update",
            "record",
            "verify",
            "verify that",
            "check",
            "status",
            "paid",
            "overdue",
            "finance system",
        ]

        has_intent = any(
            signal in normalized
            for signal in intent_signals
        )

        vague_signals = [
            "handle",
            "process",
            "manage",
            "deal with",
            "take care of",
            "look into",
            "do something with",
        ]

        is_vague = any(
            signal in normalized
            for signal in vague_signals
        )

        if is_vague and not has_intent:
            return {
                "clear": False,
                "reason": "ambiguous_invoice_action",
                "question": (
                    "What would you like me to do with the invoice?"
                ),
                "options": [
                    "Find/extract invoice details",
                    "Update the finance system",
                    "Verify the invoice",
                ],
            }

        if not has_intent:
            return {
                "clear": False,
                "reason": "missing_invoice_action",
                "question": "What should I do with the invoice?",
                "options": [
                    "Find/extract invoice details",
                    "Update the finance system",
                    "Verify the invoice",
                ],
            }

        return {
            "clear": True,
            "reason": None,
            "question": None,
            "options": [],
        }


    def execute_task(
        self,
        task: str,
        simulate_failure: bool = False,
        approval_granted: bool = False,
        resume_context: Optional[
            Dict[str, Any]
        ] = None,
    ) -> Dict[str, Any]:

        # --------------------------------------------------------
        # SAFETY / CLARIFICATION GATE
        #
        # Do not ask the planner to invent missing user intent.
        # --------------------------------------------------------
        clarity = self.analyze_task_clarity(task)

        if not clarity.get("clear", False):
            self.log(
                "clarification_required",
                {
                    "reason": clarity.get("reason"),
                    "question": clarity.get("question"),
                    "options": clarity.get("options", []),
                },
            )

            return {
                "success": False,
                "run_id": self.run_id,
                "status": "needs_clarification",
                "goal": None,
                "clarification_question": clarity.get("question"),
                "clarification_options": clarity.get("options", []),
                "reason": clarity.get("reason"),
                "step_results": [],
                "evidence": self.execution_log,
            }

        task = str(
            task
        ).strip()

        # ========================================================
        # APPROVAL RESUME
        # ========================================================

        if approval_granted:

            pause_state = (
                resume_context
                if isinstance(
                    resume_context,
                    dict,
                )
                else (
                    self._find_latest_paused_state(
                        task
                    )
                )
            )

            if pause_state:

                self._restore_pause_state(
                    pause_state
                )

                plan = pause_state.get(
                    "plan"
                )

                if not isinstance(
                    plan,
                    dict,
                ):

                    return {
                        "success": False,
                        "run_id": (
                            self.run_id
                        ),
                        "status": (
                            "invalid_pause_state"
                        ),
                        "error": (
                            "Persisted plan is invalid."
                        ),
                        "evidence": (
                            self.execution_log
                        ),
                    }

                step_results = pause_state.get(
                    "step_results",
                    [],
                )

                if not isinstance(
                    step_results,
                    list,
                ):

                    step_results = []

                next_step_index = int(
                    pause_state.get(
                        "next_step_index",
                        0,
                    )
                )

                persisted_failure_mode = bool(
                    pause_state.get(
                        "simulate_failure",
                        simulate_failure,
                    )
                )

                return self._execute_plan(
                    task=task,
                    plan=plan,
                    step_results=(
                        step_results
                    ),
                    start_step_index=(
                        next_step_index
                    ),
                    simulate_failure=(
                        persisted_failure_mode
                    ),
                    approval_granted=True,
                    resumed=True,
                    previous_pause_state=(
                        pause_state
                    ),
                )

        # ========================================================
        # FRESH EXECUTION
        # ========================================================

        self.log(
            "task_received",
            {
                "run_id": self.run_id,
                "task": task,
                "approval_granted": (
                    approval_granted
                ),
            },
        )

        # --------------------------------------------------------
        # Planner
        # --------------------------------------------------------

        try:

            plan = (
                self.planner.create_plan(
                    task
                )
            )

        except Exception as exc:

            self.log(
                "planning_failed",
                {
                    "error": str(exc),
                },
            )

            return {
                "success": False,
                "run_id": (
                    self.run_id
                ),
                "status": (
                    "planning_failed"
                ),
                "error": str(exc),
                "evidence": (
                    self.execution_log
                ),
            }

        self.log(
            "plan_created",
            plan,
        )

        return self._execute_plan(
            task=task,
            plan=plan,
            step_results=[],
            start_step_index=0,
            simulate_failure=(
                simulate_failure
            ),
            approval_granted=(
                approval_granted
            ),
            resumed=False,
            previous_pause_state=None,
        )


# ============================================================
# LOCAL DEMO
# ============================================================

if __name__ == "__main__":

    task = (
        "Find the latest invoice from Acme, "
        "extract the amount and due date, "
        "enter it into the internal finance system, "
        "and verify that the update was completed correctly."
    )

    engine = ExecutionEngine()

    result = engine.execute_task(
        task,
        simulate_failure=True,
        approval_granted=True,
    )

    print()
    print("=" * 70)
    print("FINAL RESULT")
    print("=" * 70)

    print(
        json.dumps(
            result,
            indent=2,
            default=str,
        )
    )
