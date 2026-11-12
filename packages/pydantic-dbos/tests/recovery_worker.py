"""Deterministic model transport for the native DBOS recovery test."""

import asyncio
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from dbos import DBOS, SetWorkflowID
from pydantic_ai import Agent, NativeOutput, StructuredDict
from pydantic_ai.durable_exec.dbos import DBOSDurability
from pydantic_ai.messages import (
    Citation,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    WebCitationSource,
)
from pydantic_ai.models.function import FunctionModel

from dbos_report.agent import agent as weather_agent
from dbos_report.agent import report
from dbos_report.tools import web_search
from weather_core.report import REPORT_SCHEMA

fixture = json.loads((Path(__file__).resolve().parents[2] / "core/tests/report.json").read_text())
phase = os.environ["DBOS_TEST_PHASE"]


async def model(messages, info):
    assert info.model_settings["parallel_tool_calls"] is False
    assert [tool.name for tool in info.function_tools] == ["web_search"]
    results = [
        part for message in messages for part in message.parts if isinstance(part, ToolReturnPart)
    ]
    if not results:
        return ModelResponse(
            parts=[
                ToolCallPart("web_search", {"query": "tomorrow Budapest"}, tool_call_id="search-1")
            ]
        )
    assert results[0].content["answer"] == "Saved forecast"
    assert results[0].content["sources"][0].url == "https://example.com/forecast"
    if phase == "block":
        print("MODEL_WAITING_AFTER_SAVED_SEARCH", flush=True)
        await asyncio.Event().wait()
    return ModelResponse(parts=[TextPart(json.dumps(fixture))])


test_agent = Agent(
    FunctionModel(model),
    name="dbos_replay_test",
    tools=[web_search],
    model_settings=weather_agent.model_settings,
    output_type=NativeOutput(StructuredDict(REPORT_SCHEMA), strict=True),
    capabilities=[DBOSDurability()],
)
search = AsyncMock(
    return_value=SimpleNamespace(
        output="Saved forecast",
        response=ModelResponse(
            parts=[
                TextPart(
                    "Saved forecast",
                    citations=[
                        Citation(
                            sources=[
                                WebCitationSource(
                                    url="https://example.com/forecast", title="Test source"
                                )
                            ]
                        ),
                    ],
                )
            ]
        ),
    )
)
if phase == "resume":
    search.side_effect = AssertionError("A completed web_search step was executed again")

with (
    patch("dbos_report.agent.agent", test_agent),
    patch("dbos_report.tools.search_agent.run", search),
):
    DBOS(
        config={
            "name": "dbos-replay-test",
            "system_database_url": os.environ["DBOS_TEST_DATABASE_URL"],
            "application_version": "search-replay-test",
            "enable_otlp": False,
            "log_level": "ERROR",
        }
    )
    DBOS.launch()
    try:
        if phase == "block":
            with SetWorkflowID("search-replay"):
                handle = DBOS.start_workflow(report, "search-replay")
        else:
            handle = DBOS.retrieve_workflow("search-replay")
        assert handle.get_result() == fixture
        assert search.await_count == 0
        print("REPORT_COMPLETED_WITH_SAVED_SEARCH", flush=True)
    finally:
        DBOS.destroy()
