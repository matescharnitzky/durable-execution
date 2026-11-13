from absurd_sdk import AsyncAbsurd, AsyncTaskContext, JsonValue

from absurd_report.agent import agent
from absurd_report.config import Settings
from weather_core.report import validate_report


def runtime() -> AsyncAbsurd:
    """Create a client and register the native task handler."""
    client = AsyncAbsurd(Settings().absurd_database_url.get_secret_value(), queue_name="weather")

    @client.register_task(name="weather-report")
    async def report(payload: JsonValue, ctx: AsyncTaskContext) -> JsonValue:
        """Execute the agent inside the native durable task context."""
        if not isinstance(payload, dict) or not isinstance(payload.get("run_id"), str):
            raise ValueError("Expected a run_id string")
        result = await agent.run(
            "Generate the weather report.",
            metadata={"durable.runtime": "absurd", "durable.run_id": payload["run_id"]},
        )
        return validate_report(result.output)

    return client
