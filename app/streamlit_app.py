import html
import sys
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent.parent

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.execution_engine import ExecutionEngine


# ============================================================
# PAGE
# ============================================================

st.set_page_config(
    page_title="CentrAlign AI",
    page_icon="C",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# HELPERS
# ============================================================

def money(value):
    try:
        return f"â‚¹{float(value):,.0f}"
    except Exception:
        return "â€”"


def step_core(step):
    if not isinstance(step, dict):
        return {}

    result = step.get("result", step)

    if isinstance(result, dict):
        nested = result.get("result")

        if isinstance(nested, dict):
            return nested

        return result

    return {}


def invoice_from_result(result):
    if not isinstance(result, dict):
        return None

    steps = result.get("step_results", [])

    if not isinstance(steps, list):
        return None

    for step in steps:

        core = step_core(step)

        invoice = core.get("invoice")

        if isinstance(invoice, dict):
            return invoice

        extracted = core.get("extracted")

        if isinstance(extracted, dict):
            return extracted

    return None


def approval_amount(result):
    invoice = invoice_from_result(result)

    if invoice:
        return invoice.get("amount")

    return result.get("amount")


def tool_name(tool):
    return {
        "search_invoices": "Invoice search",
        "read_invoice": "Invoice extraction",
        "update_finance_system": "Finance system update",
        "verify_invoice": "Outcome verification",
        "request_human_approval": "Human approval",
    }.get(tool, "Worker action")


def step_detail(step):
    tool = step.get("tool", "")
    core = step_core(step)

    if tool == "search_invoices":

        company = (
            core.get("company")
            or core.get("vendor")
            or "the requested company"
        )

        count = core.get("count")

        if count is not None:
            return f"Reviewed {count} matching invoice(s) for {company}."

        return f"Located the relevant invoice records for {company}."

    if tool == "read_invoice":

        invoice = core.get("invoice", {})

        if isinstance(invoice, dict):
            return (
                f"Extracted {money(invoice.get('amount'))} "
                f"with due date {invoice.get('due_date', 'â€”')}."
            )

        return "Read the invoice and extracted the required fields."

    if tool == "update_finance_system":

        amount = core.get("amount")
        due_date = core.get("due_date")

        # Recovery results may expose the repaired values under
        # alternate fields.
        if amount is None:
            amount = core.get("expected_amount")

        if due_date is None:
            due_date = core.get("expected_due_date")

        if amount is not None and due_date is not None:
            return (
                f"Saved {money(amount)} "
                f"with due date {due_date}."
            )

        return "Updated the finance record with the corrected invoice values."

    if tool == "verify_invoice":

        verified = core.get("verified")

        if verified is True:
            return "Amount and due date match the trusted invoice."

        if verified is False:
            return "Verification detected a mismatch in the saved record."

        return "Checked the saved finance record."

    if tool == "request_human_approval":

        return core.get(
            "message",
            "Worker paused for the required human decision.",
        )

    return "Completed an autonomous worker action."


def clear_state():

    for key in [
        "last_result",
        "approval_pending",
        "pending_task",
        "pending_failure_mode",
        "clarification_pending",
        "pending_clarification_task",
        "clarified_task",
        "clarification_choice",
    ]:
        st.session_state.pop(key, None)


def execute_worker(task_text, approval_granted=False):

    engine = ExecutionEngine()

    try:

        return engine.execute_task(
            task_text,
            simulate_failure=st.session_state.get(
                "failure_mode",
                False,
            ),
            approval_granted=approval_granted,
        )

    except TypeError:

        return engine.execute_task(
            task_text
        )


def friendly_status(result):

    status = result.get("status", "")

    if status == "completed":
        return "Completed"

    if status == "awaiting_human_approval":
        return "Awaiting approval"

    if status == "needs_clarification":
        return "Needs clarification"

    if status == "rejected":
        return "Rejected"

    if result.get("success") is False:
        return "Attention needed"

    return status or "Active"


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.title("CentrAlign AI")

    st.caption("Autonomous task worker")

    st.divider()

    st.subheader("Worker status")

    st.success("Worker online")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Runtime", "Ready")

    with col2:
        st.metric("Policy", "Active")

    st.divider()

    st.subheader("Demo scenarios")

    if st.button(
        "Latest Acme invoice",
        use_container_width=True,
        key="scenario_acme",
    ):

        st.session_state["task_input"] = (
            "Find the latest invoice from Acme, extract the amount and "
            "due date, enter it into the internal finance system, and "
            "verify that the update was completed correctly."
        )

    if st.button(
        "Verification workflow",
        use_container_width=True,
        key="scenario_verify",
    ):

        st.session_state["task_input"] = (
            "Verify that the latest Acme invoice is correctly recorded "
            "in the internal finance system."
        )

    if st.button(
        "Clarification demo",
        use_container_width=True,
        key="scenario_clarify",
    ):

        st.session_state["task_input"] = (
            "Find the latest invoice."
        )

    st.divider()

    st.subheader("Reliability lab")

    st.checkbox(
        "Inject one recoverable verification failure",
        key="failure_mode",
    )

    st.caption(
        "Demonstrates mismatch detection, recovery and re-verification."
    )

    st.divider()

    if st.button(
        "Clear current run",
        use_container_width=True,
        key="clear_current_run",
    ):

        clear_state()

        st.rerun()


# ============================================================
# HERO
# ============================================================

st.title(
    "Give the worker a goal. It figures out the work."
)

st.caption(
    "CentrAlign interprets the goal, plans the work, uses company tools, "
    "observes results, handles failures, verifies the outcome, and asks "
    "for human input when it cannot safely continue."
)


# ============================================================
# TASK COMPOSER
# ============================================================

st.subheader("Task")

st.caption(
    "Describe the outcome in natural language."
)

if "task_input" not in st.session_state:

    st.session_state["task_input"] = (
        "Find the latest invoice from Acme, extract the amount and "
        "due date, enter it into the internal finance system, and "
        "verify that the update was completed correctly."
    )

task = st.text_area(
    "Task",
    key="task_input",
    height=120,
    label_visibility="collapsed",
    placeholder=(
        "Example: Find the latest Acme invoice, update the finance "
        "system, and verify it."
    ),
)

run_clicked = st.button(
    "Run Autonomous Worker",
    type="primary",
    use_container_width=True,
    key="run_worker",
)


# ============================================================
# RUN WORKER
# ============================================================

if run_clicked:

    # Clear the state belonging to the previous run.
    for key in [
        "last_result",
        "approval_pending",
        "pending_task",
        "pending_failure_mode",
        "clarification_pending",
        "pending_clarification_task",
    ]:
        st.session_state.pop(key, None)

    task_to_run = st.session_state.pop(
        "clarified_task",
        None,
    )

    if not task_to_run:

        task_to_run = task.strip()

    if not task_to_run:

        st.warning(
            "Please enter a task first."
        )

        st.stop()

    with st.spinner(
        "CentrAlign is working through the task..."
    ):

        result = execute_worker(
            task_to_run,
            approval_granted=False,
        )

    st.session_state["last_result"] = result

    if isinstance(result, dict):

        status = result.get("status")

        if status == "needs_clarification":

            st.session_state["clarification_pending"] = True

            st.session_state[
                "pending_clarification_task"
            ] = task_to_run

        else:

            st.session_state["clarification_pending"] = False

        if status == "awaiting_human_approval":

            st.session_state["approval_pending"] = True

            st.session_state["pending_task"] = task_to_run

            st.session_state[
                "pending_failure_mode"
            ] = st.session_state.get(
                "failure_mode",
                False,
            )

        else:

            st.session_state["approval_pending"] = False

    st.rerun()


# ============================================================
# RESULT
# ============================================================

result = st.session_state.get(
    "last_result"
)

if isinstance(result, dict):

    status = result.get(
        "status",
        "",
    )


    # ========================================================
    # CLARIFICATION
    # ========================================================

    if (
        status == "needs_clarification"
        and st.session_state.get(
            "clarification_pending",
            False,
        )
    ):

        st.subheader(
            "Clarification needed"
        )

        st.info(
            result.get(
                "clarification_question",
                "I need a little more information before I can safely proceed.",
            )
        )

        options = result.get(
            "clarification_options",
            [],
        )

        if options:

            selected = st.radio(
                "Choose how the worker should proceed",
                options,
                key="clarification_choice",
            )

        else:

            selected = st.text_input(
                "Your clarification",
                key="clarification_choice",
            )

        if st.button(
            "Run Clarified Task",
            type="primary",
            use_container_width=True,
            key="run_clarified_task",
        ):

            original_task = st.session_state.get(
                "pending_clarification_task",
                task,
            )

            clarified_task = (
                original_task
                + "\n\nUser clarification: "
                + selected.strip()
            )

            st.session_state["clarified_task"] = (
                clarified_task
            )

            st.session_state[
                "clarification_pending"
            ] = False

            st.rerun()


    # ========================================================
    # HUMAN APPROVAL
    # ========================================================

    if (
        status == "awaiting_human_approval"
        and st.session_state.get(
            "approval_pending",
            False,
        )
    ):

        st.subheader(
            "Human checkpoint"
        )

        st.warning(
            "This action requires human approval before the "
            "finance record can be changed."
        )

        invoice = invoice_from_result(
            result
        ) or {}

        invoice_id = (
            invoice.get("invoice_id")
            or result.get("invoice_id")
            or "Invoice"
        )

        amount = (
            invoice.get("amount")
            or approval_amount(result)
        )

        c1, c2, c3 = st.columns(3)

        with c1:
            st.metric(
                "Invoice",
                str(invoice_id),
            )

        with c2:
            st.metric(
                "Amount",
                money(amount),
            )

        with c3:
            st.metric(
                "Approval threshold",
                "â‚¹75,000",
            )

        st.caption(
            "The worker has completed the safe preparatory work "
            "and paused before the sensitive action."
        )

        approve_col, reject_col = st.columns(2)

        with approve_col:

            approve = st.button(
                "Approve & Continue",
                type="primary",
                use_container_width=True,
                key="approve_action",
            )

        with reject_col:

            reject = st.button(
                "Reject",
                use_container_width=True,
                key="reject_action",
            )

        if approve:

            with st.spinner(
                "Approval received. Finishing the task..."
            ):

                resumed_result = execute_worker(
                    st.session_state.get(
                        "pending_task",
                        task,
                    ),
                    approval_granted=True,
                )

            st.session_state[
                "last_result"
            ] = resumed_result

            st.session_state[
                "approval_pending"
            ] = False

            st.rerun()

        if reject:

            st.session_state[
                "approval_pending"
            ] = False

            st.session_state[
                "last_result"
            ] = {
                "success": False,
                "status": "rejected",
                "goal": result.get(
                    "goal",
                    task,
                ),
                "step_results": result.get(
                    "step_results",
                    [],
                ),
                "evidence": result.get(
                    "evidence",
                    [],
                ),
            }

            st.rerun()


    # ========================================================
    # STATUS
    # ========================================================

    if status == "completed" and result.get("success"):

        st.success(
            "Task completed and verified."
        )

        st.caption(
            "The requested business outcome was completed and "
            "confirmed against the source data."
        )

    elif status == "rejected":

        st.warning(
            "Action rejected. No sensitive finance change was approved."
        )

    elif status == "needs_clarification":

        if not st.session_state.get(
            "clarification_pending",
            False,
        ):

            st.info(
                "The worker paused safely because additional "
                "information is required."
            )

    elif (
        status == "awaiting_human_approval"
    ):

        # The approval panel above handles this state.
        pass

    elif result.get("success") is False:

        st.error(
            "The worker could not finish the task."
        )

        st.caption(
            "Review the execution path below to see where execution stopped."
        )


    # ========================================================
    # RUN OVERVIEW
    # ========================================================

    st.subheader(
        "Run overview"
    )

    st.caption(
        "Human-readable summary of the worker's execution."
    )

    steps = result.get(
        "step_results",
        [],
    )

    if not isinstance(steps, list):
        steps = []

    verification_ok = any(
        step_core(step).get(
            "verified"
        ) is True
        for step in steps
    )

    recovery_used = bool(
        result.get(
            "recovery_used"
        )
    )

    approval_used = bool(
        result.get(
            "approval_used"
        )
        or result.get(
            "approved"
        )
    )

    k1, k2, k3, k4 = st.columns(4)

    with k1:
        st.metric(
            "Status",
            friendly_status(result),
        )

    with k2:
        st.metric(
            "Actions",
            len(steps),
        )

    with k3:
        st.metric(
            "Verification",
            "Passed"
            if verification_ok
            else "Pending",
        )

    with k4:
        st.metric(
            "Recovery",
            "Used"
            if recovery_used
            else "Not triggered",
        )


    # ========================================================
    # EXECUTION PATH
    # ========================================================

    st.subheader(
        "Execution path"
    )

    st.caption(
        "What the worker actually did."
    )

    for index, step in enumerate(
        steps,
        start=1,
    ):

        tool = step.get(
            "tool",
            "",
        )

        core = step_core(
            step
        )

        verified_step = core.get(
            "verified"
        )

        raw_result = step.get(
            "result",
            {},
        )

        success_value = None

        if isinstance(
            raw_result,
            dict,
        ):

            success_value = raw_result.get(
                "success"
            )

        # Give recovery repair steps a clearer operator-facing name.
        display_tool = tool_name(tool)

        detail_text = step_detail(step)

        if (
            tool == "update_finance_system"
            and (
                "â€”" in detail_text
                or "corrected" in detail_text.lower()
            )
            and index > 3
        ):
            display_tool = "Recovery update"

            repair_amount = (
                core.get("amount")
                or core.get("expected_amount")
            )

            repair_due_date = (
                core.get("due_date")
                or core.get("expected_due_date")
            )

            if repair_amount is not None and repair_due_date is not None:
                detail_text = (
                    f"Repaired the finance record to "
                    f"{money(repair_amount)} with due date "
                    f"{repair_due_date}."
                )
            else:
                detail_text = (
                    "Repaired the finance record using trusted "
                    "invoice data before re-verification."
                )

        st.markdown(
            f"**{index}. {display_tool}**"
        )

        st.caption(
            detail_text
        )

        if verified_step is True:

            st.success(
                "Verified",
                icon="âœ…",
            )

        elif verified_step is False:

            st.warning(
                "Mismatch detected",
                icon="âš ï¸",
            )

        elif success_value is False:

            st.error(
                "Failed",
                icon="âŒ",
            )

        else:

            st.success(
                "Completed",
                icon="âœ…",
            )

    if recovery_used:

        st.info(
            "Recovery used: the worker detected an incorrect "
            "business state, repaired it using trusted invoice "
            "data, and verified the corrected state."
        )


    # ========================================================
    # BUSINESS RESULT
    # ========================================================

    st.subheader(
        "Business result"
    )

    invoice = invoice_from_result(
        result
    )

    if invoice:

        b1, b2, b3 = st.columns(3)

        with b1:
            st.metric(
                "Invoice",
                str(
                    invoice.get(
                        "invoice_id",
                        "â€”",
                    )
                ),
            )

        with b2:
            st.metric(
                "Amount",
                money(
                    invoice.get(
                        "amount"
                    )
                ),
            )

        with b3:
            st.metric(
                "Due date",
                str(
                    invoice.get(
                        "due_date",
                        "â€”",
                    )
                ),
            )

        st.caption(
            f"Company: {invoice.get('company', 'â€”')}  â€¢  "
            f"Status: {invoice.get('status', 'â€”')}"
        )

    else:

        st.info(
            "No invoice snapshot was produced in this run."
        )


    # ========================================================
    # HUMAN OVERSIGHT
    # ========================================================

    if approval_used:

        st.info(
            "Human oversight was required and handled.",
            icon="ðŸ‘¤",
        )

    elif status == "awaiting_human_approval":

        st.warning(
            "Waiting for human approval.",
            icon="ðŸ‘¤",
        )

    else:

        st.caption(
            "Human oversight is enforced by company policy when required."
        )


    # ========================================================
    # ACTIVITY
    # ========================================================

    evidence = result.get(
        "evidence",
        [],
    )

    if isinstance(
        evidence,
        list
    ) and evidence:

        with st.expander(
            "Activity",
            expanded=False,
        ):

            for event in evidence:

                if not isinstance(
                    event,
                    dict,
                ):
                    continue

                event_name = event.get(
                    "event",
                    "worker_event",
                )

                display_name = (
                    str(event_name)
                    .replace(
                        "_",
                        " ",
                    )
                    .title()
                )

                st.write(
                    display_name
                )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "CentrAlign AI Â· Autonomous task execution sandbox"
)

