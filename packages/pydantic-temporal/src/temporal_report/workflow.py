from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from pydantic_ai.durable_exec.temporal import PydanticAIWorkflow

    from temporal_report.agent import agent
    from weather_core.report import validate_report


@workflow.defn
class WeatherReport(PydanticAIWorkflow):
    """Run the weather agent with native Temporal activity persistence."""

    __pydantic_ai_agents__ = [agent]

    @workflow.run
    async def run(self) -> dict:
        """Generate and validate the report using durable agent calls."""
        result = await agent.run(
            "Generate the weather report.",
            metadata={"durable.runtime": "temporal", "durable.run_id": workflow.info().workflow_id},
        )
        return validate_report(result.output)
