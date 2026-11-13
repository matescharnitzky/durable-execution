import asyncio
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from pydantic_ai import Agent, NativeOutput, StructuredDict
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai_harness.pgtask import PGTaskDurability

from pgtask_report import runtime
from pgtask_report.tools import web_search
from weather_core.report import REPORT_SCHEMA

fixture = json.loads((Path(__file__).resolve().parents[2] / "core/tests/report.json").read_text())


async def model(messages, info):
    results = [p for m in messages for p in m.parts if isinstance(p, ToolReturnPart)]
    if not results:
        return ModelResponse(parts=[ToolCallPart("web_search", {"query": "Budapest"})])
    assert results[0].content["answer"] == "Saved forecast"
    if os.environ["TEST_PHASE"] == "block":
        print("SAVED_SEARCH", flush=True)
        await asyncio.Event().wait()
    return ModelResponse(parts=[TextPart(json.dumps(fixture))])


agent = Agent(
    FunctionModel(model),
    name="pgtask_weather",
    tools=[web_search],
    model_settings={"parallel_tool_calls": False},
    output_type=NativeOutput(StructuredDict(REPORT_SCHEMA), strict=True),
    capabilities=[PGTaskDurability()],
)
search = AsyncMock(
    return_value=SimpleNamespace(output="Saved forecast", response=ModelResponse(parts=[]))
)
if os.environ["TEST_PHASE"] == "resume":
    search.side_effect = AssertionError("Completed search executed again")


async def main():
    from pgtask import Worker

    await Worker(
        os.environ["PGTASK_DATABASE_URL"],
        runtime.tasks,
        lease_duration=2,
        poll_interval=0.1,
        retention_enabled=False,
    ).run()


with patch.object(runtime, "agent", agent), patch("pgtask_report.tools.search_agent.run", search):
    asyncio.run(main())
