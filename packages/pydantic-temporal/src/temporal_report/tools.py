from pydantic_ai import Agent, WebSearchTool
from pydantic_ai.capabilities import Instrumentation, NativeTool
from pydantic_ai.messages import TextPart, WebCitationSource
from pydantic_ai.models.instrumented import InstrumentationSettings

from temporal_report.config import Settings

search_agent = Agent(
    f"openai-responses:{Settings().openai_model}",
    defer_model_check=True,
    name="temporal_web_search",
    instructions="Search public web pages for the query and cite their HTTP(S) URLs. Do not use weather widgets, internal reference IDs, or placeholder URLs as sources.",
    capabilities=[
        NativeTool(WebSearchTool()),
        Instrumentation(InstrumentationSettings(include_content=False)),
    ],
)


async def web_search(query: str) -> dict:
    """Search the web for current information and source URLs."""
    result = await search_agent.run(query)
    sources = [
        source
        for part in result.response.parts if isinstance(part, TextPart)
        for citation in part.citations or []
        for source in citation.sources if isinstance(source, WebCitationSource)
    ]
    return {"answer": result.output, "sources": sources}
