import logfire
from dbos import DBOS
from pydantic_ai import Agent, NativeOutput, StructuredDict, WebSearchTool
from pydantic_ai.capabilities import Instrumentation, NativeTool
from pydantic_ai.durable_exec.dbos import DBOSDurability
from pydantic_ai.models.instrumented import InstrumentationSettings

from dbos_report.config import Settings
from weather_core.prompts import SYSTEM_PROMPT
from weather_core.report import REPORT_SCHEMA, validate_report

agent = Agent(
    f"openai-responses:{Settings().openai_model}",
    defer_model_check=True,
    name="dbos_weather",
    instructions=SYSTEM_PROMPT,
    output_type=NativeOutput(StructuredDict(REPORT_SCHEMA), strict=True),
    capabilities=[
        NativeTool(WebSearchTool()),
        DBOSDurability(),
        Instrumentation(InstrumentationSettings(include_content=False)),
    ],
)


@DBOS.workflow()
async def report(run_id: str) -> dict:
    with logfire.span("DBOS report", **{"durable.runtime": "dbos", "durable.run_id": run_id}):
        result = await agent.run(
            "Generate the weather report.",
            metadata={"durable.runtime": "dbos", "durable.run_id": run_id},
        )
        return validate_report(result.output)
