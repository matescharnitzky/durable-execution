from pydantic_ai import Agent, WebSearchTool
from pydantic_ai.capabilities import Instrumentation, NativeTool
from pydantic_ai.models.instrumented import InstrumentationSettings

from temporal_report.config import Settings

search_agent = Agent(
    f"openai-responses:{Settings().openai_model}",
    defer_model_check=True,
    name="temporal_web_search",
    instructions="Search the web for the query and include public source URLs in your answer.",
    capabilities=[
        NativeTool(WebSearchTool()),
        Instrumentation(InstrumentationSettings(include_content=False)),
    ],
)


async def web_search(query: str) -> str:
    """Search the web for current information and source URLs."""
    result = await search_agent.run(query)
    return result.output
