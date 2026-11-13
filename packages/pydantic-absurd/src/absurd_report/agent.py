from pydantic_ai import Agent, NativeOutput, StructuredDict
from pydantic_ai.capabilities import Instrumentation
from pydantic_ai.models.instrumented import InstrumentationSettings
from pydantic_ai_harness.absurd import AbsurdDurability

from absurd_report.config import Settings
from absurd_report.tools import web_search
from weather_core.prompts import SYSTEM_PROMPT
from weather_core.report import REPORT_SCHEMA

agent = Agent(
    f"openai-responses:{Settings().openai_model}",
    defer_model_check=True,
    name="absurd_weather",
    instructions=SYSTEM_PROMPT,
    output_type=NativeOutput(StructuredDict(REPORT_SCHEMA), strict=True),
    model_settings={"parallel_tool_calls": False},
    tools=[web_search],
    capabilities=[
        AbsurdDurability(),
        Instrumentation(InstrumentationSettings(include_content=False)),
    ],
)
