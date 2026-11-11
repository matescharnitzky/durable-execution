from pydantic_ai import Agent, NativeOutput, StructuredDict
from pydantic_ai.capabilities import Instrumentation
from pydantic_ai.durable_exec.temporal import TemporalDurability
from pydantic_ai.models.instrumented import InstrumentationSettings

from temporal_report.config import Settings
from temporal_report.tools import web_search
from weather_core.prompts import SYSTEM_PROMPT
from weather_core.report import REPORT_SCHEMA

agent = Agent(
    f"openai-responses:{Settings().openai_model}",
    defer_model_check=True,
    name="temporal_weather",
    instructions=SYSTEM_PROMPT,
    output_type=NativeOutput(StructuredDict(REPORT_SCHEMA), strict=True),
    tools=[web_search],
    model_settings={"parallel_tool_calls": False},
    capabilities=[
        TemporalDurability(),
        Instrumentation(InstrumentationSettings(include_content=False)),
    ],
)
