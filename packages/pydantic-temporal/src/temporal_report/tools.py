from pydantic_ai import Agent, WebSearchTool
from pydantic_ai.capabilities import NativeTool
from pydantic_ai.messages import TextPart, WebCitationSource

from temporal_report.config import Settings
from weather_core.prompts import WEB_SEARCH_INSTRUCTIONS

search_agent = Agent(
    f"openai-responses:{Settings().openai_model}",
    defer_model_check=True,
    name="temporal_web_search",
    instructions=WEB_SEARCH_INSTRUCTIONS,
    capabilities=[
        NativeTool(WebSearchTool()),
    ],
)


async def web_search(query: str) -> dict:
    """Search the web for current information and source URLs."""
    result = await search_agent.run(query)
    sources = [
        source
        for part in result.response.parts
        if isinstance(part, TextPart)
        for citation in part.citations or []
        for source in citation.sources
        if isinstance(source, WebCitationSource)
    ]
    return {"answer": result.output, "sources": sources}
