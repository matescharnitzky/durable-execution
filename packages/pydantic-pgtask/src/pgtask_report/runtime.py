from pgtask import Task, TaskRegistry

from pgtask_report.agent import agent
from weather_core.report import validate_report

tasks = TaskRegistry(queue_name="weather")


@tasks.task("weather-report")
async def report(task: Task, payload: dict[str, str]) -> dict:
    """Execute the agent inside the native durable task context."""
    result = await agent.run(
        "Generate the weather report.",
        metadata={"durable.runtime": "pgtask", "durable.run_id": payload["run_id"]},
    )
    return validate_report(result.output)
