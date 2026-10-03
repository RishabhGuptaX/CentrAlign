from app.agent.planner import TaskPlanner

def test_planner_understands_task():
    planner = TaskPlanner()
    result = planner.understand("Find the latest invoice")
    assert result["task"] == "Find the latest invoice"
