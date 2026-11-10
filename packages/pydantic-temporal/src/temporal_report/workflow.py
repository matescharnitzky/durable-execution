import os
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from pydantic_ai.durable_exec.temporal import PydanticAIWorkflow, TemporalDurability

    from temporal_report.agent import forecast_batches, report_agent

    agent = report_agent(TemporalDurability(model_activity_config={
        "start_to_close_timeout": timedelta(seconds=10 if os.getenv("DURABLE_FIXTURE") == "1" else 100),
        "retry_policy": RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_attempts=3,
            non_retryable_error_types=["ValidationError", "ValueError", "RuntimeError", "KeyError"],
        ),
    }))


@workflow.defn
class WeatherReport(PydanticAIWorkflow):
    __pydantic_ai_agents__ = [agent]

    @workflow.run
    async def run(self, run_id: str, forecast_date: str, city_batches: list[list[str]]) -> list[dict]:
        return await forecast_batches(agent, run_id, forecast_date, city_batches)
