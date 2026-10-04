# CentrAlign AI — Autonomous AI Task Worker

> A narrow, working prototype of an autonomous AI worker that turns a natural-language business goal into completed work using planning, tool execution, policy enforcement, human approval, failure recovery, and independent verification.

**Live Demo:** https://centralign-project.streamlit.app/  

**GitHub:** https://github.com/RishabhGuptaX/CentrAlign

---

## 1. Overview

CentrAlign AI was built for the **CentrAlign AI Engineering Hiring Assessment**.

The system is organized around the following execution loop:

**Goal → Understand → Plan → Execute → Observe → Adapt → Verify → Complete**

The user provides a business goal in natural language. The worker uses an LLM to generate a structured execution plan, executes that plan through a controlled tool layer, observes results, enforces company policy, requests human approval for sensitive actions, recovers from safe failures, and independently verifies the final business outcome.

The current prototype intentionally focuses on a controlled invoice-processing environment. This keeps the scope narrow enough to demonstrate genuine autonomy and reliability rather than claiming unsupported enterprise capabilities.

### What the worker demonstrates

- Natural-language task understanding

- LLM-based planning

- Tool selection and execution

- Step-to-step context and parameter resolution

- Policy enforcement

- Human-in-the-loop approval

- Persistent pause/resume state

- Bounded retry for transient failures

- Safe handling of semantic failures

- Independent business-outcome verification

- Verification failure recovery

- Clarification for incomplete or ambiguous tasks

- Structured execution evidence

- Human-readable execution summaries

---

# 2. Problem

Enterprise tasks often require a person to:

1\. Find information.

2\. Decide what should happen next.

3\. Perform an action in another system.

4\. Check whether the action actually worked.

5\. Recover when something goes wrong.

6\. Involve a human when an action is sensitive.

An LLM response alone does not complete this workflow.

CentrAlign treats the problem as **reliable task execution**, not simple question answering.

For example, a user can provide:

> "Find the latest invoice from Acme, extract the amount and due date, enter it into the internal finance system, and verify that the update was completed correctly."

The worker determines and executes the required sequence of actions.

---

# 3. Current Prototype

The prototype uses a simulated company environment containing invoice data, finance records, and company policy.

### Core execution flow

```text

User Goal

&#x20;  |

&#x20;  v

Task Understanding / Clarification

&#x20;  |

&#x20;  v

LLM Planning

&#x20;  |

&#x20;  v

Tool Selection

&#x20;  |

&#x20;  v

Invoice Search

&#x20;  |

&#x20;  v

Invoice Extraction

&#x20;  |

&#x20;  v

Policy Check

&#x20;  |

&#x20;  v

Human Approval (when required)

&#x20;  |

&#x20;  v

Finance System Update

&#x20;  |

&#x20;  v

Observe Result

&#x20;  |

&#x20;  v

Independent Verification

&#x20;  |

&#x20;  v

Recovery if necessary

&#x20;  |

&#x20;  v

Re-verification

&#x20;  |

&#x20;  v

Final Evidence

```

Supported simulated companies include:

- Acme

- Globex

- Initech

---

# 4. Architecture

```text

&#x20;                        +----------------------+

&#x20;                        |      User / UI       |

&#x20;                        |    Streamlit App     |

&#x20;                        +----------+-----------+

&#x20;                                   |

&#x20;                                   v

&#x20;                        +----------------------+

&#x20;                        |   Execution Engine   |

&#x20;                        |                      |

&#x20;                        | Task understanding   |

&#x20;                        | State management     |

&#x20;                        | Execution loop       |

&#x20;                        | Policy checks        |

&#x20;                        | Retry / recovery     |

&#x20;                        | Verification         |

&#x20;                        +----------+-----------+

&#x20;                                   |

&#x20;                 +-----------------+-----------------+

&#x20;                 |                                   |

&#x20;                 v                                   v

&#x20;       +------------------+                +------------------+

&#x20;       |   Task Planner   |                |    Tool Router   |

&#x20;       |                  |                |                  |

&#x20;       | Groq LLM         |                | Tool registry    |

&#x20;       | Structured plan  |                | Tool dispatch    |

&#x20;       +------------------+                +--------+---------+

&#x20;                                                    |

&#x20;                +-----------------------------------+----------------------+

&#x20;                |                                   |                      |

&#x20;                v                                   v                      v

&#x20;       Invoice Search                       Invoice Reader          Finance System

&#x20;                |                                   |                      |

&#x20;                +-------------------+---------------+----------------------+

&#x20;                                    |

&#x20;                                    v

&#x20;                            Verification Tool

&#x20;                                    |

&#x20;                                    v

&#x20;                             Human Approval

```

## Main Components

### `app/execution_engine.py`

The central runtime responsible for:

- Executing tasks

- Managing execution state

- Resolving references between steps

- Normalizing planner parameters

- Enforcing company policy

- Pausing and resuming execution

- Bounded retry behavior

- Independent verification

- Failure recovery

- Evidence generation

### `app/agent_planner.py`

Uses the LLM to convert a natural-language goal into a structured execution plan.

The planner identifies:

- Goal

- Actions

- Tool selection

- Parameters

- Possible approval requirements

The planner **proposes** actions, while the deterministic execution runtime controls what is actually allowed to execute.

### `app/tool_router.py`

Central registry and dispatcher for the available tools.

Current tools:

- `search_invoices`

- `read_invoice`

- `update_finance_system`

- `verify_invoice`

- `request_human_approval`

### `app/tools/`

Contains the simulated company tools for:

- Invoice search

- Invoice extraction

- Finance-system updates

- Invoice verification

- Human approval

### `data/`

Contains the controlled company environment:

```text

data/

├── invoices/

├── finance/

└── company_policy.json

```

---

# 5. Important Technical and Design Decisions

## 5.1 LLM proposes; deterministic runtime controls execution

The LLM is used for task understanding and plan generation.

The execution engine remains responsible for:

- Policy enforcement

- Parameter normalization

- Tool execution

- Human approval

- Retry behavior

- Verification

- Recovery

- State persistence

This reduces the risk of allowing an LLM to bypass business controls.

---

## 5.2 Policy-driven human approval

The simulated company policy defines a high-value threshold of **INR 75,000**.

The latest Acme invoice used in the main demonstration is:

```text

Invoice: ACME-2026-003

Amount: INR 84,500

```

Because the amount exceeds the configured threshold, the worker pauses before modifying the finance system and requests human approval.

The policy check is enforced by the execution engine rather than trusting the planner alone.

The flow is:

```text

Safe preparatory work

&#x20;       |

&#x20;       v

Policy check

&#x20;       |

&#x20;       v

Human approval required

&#x20;       |

&#x20;       v

Pause

&#x20;       |

&#x20;       v

Approve / Reject

```

---

## 5.3 Resumable execution

When approval is required, the worker:

1\. Completes safe preparatory work.

2\. Persists execution state.

3\. Pauses before the sensitive action.

4\. Waits for human approval.

5\. Restores the paused execution state.

6\. Resumes from the blocked step.

This avoids unnecessarily repeating already completed work.

---

## 5.4 Independent verification

A successful tool call is not treated as proof that the business objective was achieved.

The verification tool compares the saved finance record against trusted invoice information.

The system therefore distinguishes:

```text

Tool execution success

&#x20;       !=

Business outcome verified

```

The final completion state is based on the verified business result rather than merely on a successful tool invocation.

---

## 5.5 Bounded retries

Only failures considered transient are retried.

Examples include:

- Timeout

- Temporary service unavailability

- Connection reset or refused

- Rate limiting

- HTTP 500/502/503/504

Semantic or business failures such as:

```text

Invoice not found

```

are not blindly retried.

Retry behavior is bounded to prevent uncontrolled execution loops.

---

## 5.6 Verification failure recovery

The prototype includes a controlled failure-injection mode.

A finance update can intentionally produce an incorrect saved value.

The worker then follows:

```text

Finance Update

&#x20;     |

&#x20;     v

Verification

&#x20;     |

&#x20;     v

Mismatch Detected

&#x20;     |

&#x20;     v

Recovery using trusted invoice data

&#x20;     |

&#x20;     v

Correct Record

&#x20;     |

&#x20;     v

Re-verification

&#x20;     |

&#x20;     v

Completed

```

This demonstrates observation and adaptation rather than simply executing a predetermined sequence.

---

## 5.7 Clarification before execution

The worker does not blindly guess missing information.

For example:

```text

Find the latest invoice.

```

does not contain enough information to determine the company.

The worker therefore asks which company should be searched.

Likewise:

```text

Handle the Acme invoice.

```

is treated as ambiguous because the requested action is unclear.

The worker requests clarification before executing tools.

---

# 6. Demonstrated Scenarios

## Scenario 1 — Autonomous invoice workflow

Example task:

```text

Find the latest invoice from Acme, extract the amount and due date,

enter it into the internal finance system, and verify that the update

was completed correctly.

```

Expected flow:

```text

Search

&#x20;  ->

Extraction

&#x20;  ->

Policy Check

&#x20;  ->

Approval if required

&#x20;  ->

Finance Update

&#x20;  ->

Verification

&#x20;  ->

Completion

```

---

## Scenario 2 — Human approval

The latest Acme invoice exceeds the configured high-value threshold.

The interface displays:

```text

Invoice: ACME-2026-003

Amount: INR 84,500

Approval threshold: INR 75,000

```

The worker pauses before the sensitive finance action.

The user can:

- Approve and continue

- Reject the action

---

## Scenario 3 — Failure recovery

The Streamlit interface contains a **Reliability Lab** option:

```text

Inject one recoverable verification failure

```

When enabled, the worker demonstrates:

```text

Incorrect Update

&#x20;  ->

Verification Mismatch

&#x20;  ->

Recovery

&#x20;  ->

Corrected Update

&#x20;  ->

Re-verification

&#x20;  ->

Completed

```

---

## Scenario 4 — Clarification

Example:

```text

Find the latest invoice.

```

The worker identifies the missing company information and asks for clarification instead of guessing.

---

## Scenario 5 — Different company

The same execution engine can handle different simulated companies such as:

- Globex

- Initech

without changing the core execution engine.

---

# 7. Testing

The repository contains tests for the main reliability behaviors:

```text

tests/

├── test_autonomous_worker.py

├── test_generalization.py

├── test_failure_handling.py

└── test_clarification.py

```

The test coverage includes:

- Autonomous invoice workflows

- Different-company workflows

- Invoice extraction

- Verification-only workflows

- Human approval

- Resume after approval

- Transient failure retry

- Semantic failure handling

- Verification failure recovery

- Clarification for incomplete tasks

The generalization suite specifically exercises:

```text

Different company lookup

Different company extraction

Verification-only workflow

Human approval + resume

Failure detection + recovery

```

---

# 8. Project Structure

```text

CentrAlign/

|

├── app/

|   ├── __init__.py

|   ├── execution_engine.py

|   ├── agent_planner.py

|   ├── tool_router.py

|   |

|   ├── llm/

|   |   ├── __init__.py

|   |   └── groq_client.py

|   |

|   └── tools/

|       ├── __init__.py

|       ├── invoice_search.py

|       ├── invoice_reader.py

|       ├── finance_system.py

|       ├── invoice_verification.py

|       └── human_approval.py

|

├── data/

|   ├── invoices/

|   ├── finance/

|   └── company_policy.json

|

├── tests/

|   ├── test_autonomous_worker.py

|   ├── test_generalization.py

|   ├── test_failure_handling.py

|   └── test_clarification.py

|

├── app/streamlit_app.py

├── streamlit_app.py

├── requirements.txt

├── .env.example

├── .gitignore

└── README.md

```

---

# 9. Setup

## Prerequisites

- Python 3.10+

- Git

- Groq API key

## Clone the repository

```bash

git clone https://github.com/RishabhGuptaX/CentrAlign.git

cd CentrAlign

```

## Create a virtual environment

### Windows PowerShell

```powershell

python -m venv .venv

.\\.venv\\Scripts\\Activate.ps1

```

### macOS / Linux

```bash

python -m venv .venv

source .venv/bin/activate

```

## Install dependencies

```bash

pip install -r requirements.txt

```

## Configure the Groq API

Create a local `.env` file:

```text

GROQ_API_KEY=your_groq_api_key

GROQ_MODEL=openai/gpt-oss-20b

```

The `.env` file is excluded from Git through `.gitignore`.

**Never commit API keys or real company credentials.**

---

# 10. Run Locally

From the repository root:

```bash

streamlit run streamlit_app.py

```

The root entrypoint imports the main Streamlit application from:

```text

app/streamlit_app.py

```

---

# 11. Live Deployment

The live application is available at:

**https://centralign-project.streamlit.app/**

Deployment configuration:

```text

Repository: RishabhGuptaX/CentrAlign

Branch: main

Main file: streamlit_app.py

```

Configure Streamlit Cloud Secrets:

```toml

GROQ_API_KEY = "your_groq_api_key"

GROQ_MODEL = "openai/gpt-oss-20b"

```

The API key is not stored in the GitHub repository.

---

# 12. Models, APIs, Frameworks and External Services

## Model

**Groq API**

Configured model:

```text

openai/gpt-oss-20b

```

The model is used primarily for task understanding and execution-plan generation.

## Frameworks and libraries

- Python

- Streamlit

- Groq Python SDK

- python-dotenv

- FastAPI

- Uvicorn

- Pydantic

- Pandas

- Requests

- Pytest

## External services

- Groq API

- GitHub

- Streamlit Community Cloud

## AI-assisted development

ChatGPT was used during development for:

- Coding assistance

- Debugging

- Testing support

- Iteration and refinement

The submitted implementation and architecture were reviewed and validated during development and testing.

---

# 13. Assumptions

The prototype makes the following assumptions:

1\. The finance application can be represented by a controlled simulated system.

2\. Invoice information is available through structured files.

3\. Company policy can be represented as structured configuration.

4\. Human approval can be represented through the Streamlit interface.

5\. The available tool set is intentionally small.

6\. The prototype does not attempt to operate arbitrary websites or desktop applications.

7\. The controlled environment is sufficient to demonstrate planning, execution, observation, adaptation, verification, and human-in-the-loop behavior.

---

# 14. Known Limitations

This is a prototype rather than a production AI employee.

## Limited environment

The worker currently operates against a controlled invoice and finance environment.

It does not yet operate arbitrary enterprise websites, desktop applications, or business systems.

## Limited tool set

Only a small set of invoice and finance tools is currently available.

## LLM dependency

Planning depends partly on the LLM's ability to produce a valid structured plan.

The deterministic execution runtime provides validation, normalization, policy enforcement, retry control, and verification around the planner.

## Local persistence

Paused execution state is currently stored locally.

A production implementation would require durable shared storage.

## Single-worker execution

The prototype focuses on a single task execution flow.

It does not yet provide distributed task queues, scheduling, or multi-worker orchestration.

## Production security

A production deployment would require stronger:

- Authentication

- Authorization

- Tool permissions

- Secret management

- Audit controls

- Isolation

- Multi-tenant security

---

# 15. What I Would Build Next

## 1. Reusable connector framework

Introduce a common connector abstraction for:

```text

Browser

Files

REST APIs

Databases

Internal enterprise applications

SaaS tools

```

This would allow the same execution engine to support more enterprise workflows.

## 2. Durable execution runtime

Introduce:

- Persistent task state

- Task queues

- Background execution

- Scheduling

- Idempotency

- Distributed retries

## 3. Stronger permission model

Move from a single financial threshold to action-level authorization such as:

```text

Read

Write

Delete

Financial action

External communication

Credentialed action

High-risk action

```

Each action could then be authorized independently before execution.

## 4. Stronger verification

Add verification mechanisms such as:

- API confirmation

- Database checks

- State validation

- Document comparison

- Cross-system consistency checks

## 5. Evaluation framework

Build a broader evaluation suite measuring:

- Completion rate

- Verification accuracy

- Recovery rate

- Retry correctness

- Human intervention rate

- Cost

- Latency

- Failure modes

## 6. Enterprise memory

Add company-specific memory for:

- Policies

- Workflows

- Tool capabilities

- Terminology

- Historical outcomes

- User preferences

---

# 16. Demo Walkthrough

## Demo 1 — Normal workflow

Run:

```text

Find the latest invoice from Acme, extract the amount and due date,

enter it into the internal finance system, and verify that the update

was completed correctly.

```

Show:

```text

Search

->

Extraction

->

Human Checkpoint

->

Approval

->

Finance Update

->

Verification

->

Completion

```

## Demo 2 — Reliability

Enable:

```text

Inject one recoverable verification failure

```

Then demonstrate:

```text

Incorrect Update

->

Mismatch Detection

->

Recovery

->

Re-verification

->

Completion

```

## Demo 3 — Clarification

Run:

```text

Find the latest invoice.

```

Show that the worker requests the missing company information rather than guessing.

---

# 17. Safety and Scope

The prototype uses a simulated company environment and does not require real company credentials or unauthorized access to third-party systems.

Sensitive finance actions are controlled by simulated company policy and a human approval checkpoint.

The narrow scope is deliberate: the objective is to demonstrate genuine autonomous execution, reliability, verification, and human oversight in a controlled environment.

---

# 18. Final Links

**GitHub Repository**

https://github.com/RishabhGuptaX/CentrAlign

**Live Demo**

https://centralign-project.streamlit.app/

---

# 19. Assessment Alignment

The prototype is designed around the assessment's core evaluation areas:

```text

Autonomy

Execution

Reliability

Verification

Generalization

Engineering Quality

Product Thinking

Technical Understanding

```

The implementation prioritizes genuine task execution, controlled tool use, human oversight, failure recovery, and independent verification over feature count.

