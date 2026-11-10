"""Use the shared Responses web-search request as a Pydantic AI model turn."""

import json
from functools import partial

from pydantic_ai import Agent
from pydantic_ai.capabilities import Instrumentation
from pydantic_ai.messages import ModelResponse, TextPart, UserPromptPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.models.instrumented import InstrumentationSettings

from weather_report.forecast import search_forecast


def forecast_turn(runtime, messages, _info):
    prompt = next(part for part in messages[-1].parts if isinstance(part, UserPromptPart))
    result = search_forecast(runtime, **json.loads(prompt.content))
    return ModelResponse(parts=[TextPart(json.dumps(result))])


def report_agent(runtime, durability):
    return Agent(
        FunctionModel(partial(forecast_turn, runtime), model_name="openai-responses-web-search"),
        name=f"{runtime}_weather",
        capabilities=[durability, Instrumentation(InstrumentationSettings(include_content=False))],
    )


async def forecast_batches(agent, run_id: str, forecast_date: str, batches: list[list[str]]) -> list[dict]:
    results = []
    for batch, cities in enumerate(batches, start=1):
        prompt = json.dumps({
            "run_id": run_id, "batch": batch, "forecast_date": forecast_date, "cities": cities,
        })
        result = await agent.run(prompt)
        results.append(json.loads(result.output))
    return results
