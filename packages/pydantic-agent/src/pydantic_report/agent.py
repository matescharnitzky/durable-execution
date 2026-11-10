"""Weather agent shared by the two Pydantic AI durability backends."""

import json
import os

from openai import AsyncOpenAI
from pydantic_ai import Agent, WebSearchTool
from pydantic_ai.capabilities import Instrumentation, NativeTool
from pydantic_ai.models.instrumented import InstrumentationSettings
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider

from pydantic_report.report import FIXTURES, validate_batch

SEARCH = json.loads(FIXTURES.joinpath("search.json").read_text(encoding="utf-8"))


async def api_key() -> str:
    return os.environ["OPENAI_API_KEY"]


def report_agent(runtime, durability):
    client = AsyncOpenAI(api_key=api_key, max_retries=0, timeout=90)
    model = OpenAIResponsesModel(
        os.getenv("OPENAI_MODEL") or SEARCH["model"],
        provider=OpenAIProvider(openai_client=client),
    )
    return Agent(
        model,
        name=f"{runtime}_weather",
        instructions=SEARCH["instructions"],
        capabilities=[
            NativeTool(WebSearchTool()),
            durability,
            Instrumentation(InstrumentationSettings(include_content=False)),
        ],
    )


async def forecast_batches(agent, run_id: str, forecast_date: str, batches: list[list[str]]) -> list[dict]:
    results = []
    for batch, cities in enumerate(batches, start=1):
        prompt = json.dumps({"forecast_date": forecast_date, "cities": cities})
        result = await agent.run(prompt, metadata={"durable.run_id": run_id, "durable.batch": batch})
        text = result.output.strip().removeprefix("```json").removesuffix("```").strip()
        results.append(validate_batch(json.loads(text), forecast_date, cities))
    return results
