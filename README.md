# CentrAlign AI — Autonomous AI Task Worker

Prototype for the CentrAlign AI Engineering Hiring Assessment.

## Goal
Build a narrow but genuinely working autonomous worker that can:
- understand a natural-language task
- plan actions
- select tools
- execute actions
- observe results
- recover from failures
- maintain task state
- request approval when needed
- verify completion
- return evidence

## Current status
Scaffold only. Implementation will be built incrementally.

## Planned demo
Invoice workflow:
1. Find the latest invoice for a company.
2. Extract invoice amount and due date.
3. Update the simulated internal finance system.
4. Observe the result.
5. Recover from an injected failure when appropriate.
6. Verify the final record.
7. Return evidence and an execution summary.

## Run
```bash
pip install -r requirements.txt
streamlit run app/ui/streamlit_app.py
```
