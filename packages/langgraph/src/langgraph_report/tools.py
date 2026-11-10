"""OpenAI Responses model and its hosted web search tool."""

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from langgraph_report.config import Settings

# Passed to the Responses API, which runs the search on OpenAI’s servers.
OPENAI_WEB_SEARCH = {"type": "web_search"}


def forecast_model(settings: Settings) -> ChatOpenAI:
    def api_key() -> str:
        if settings.openai_api_key is None:
            raise ValueError("OPENAI_API_KEY is required to run the forecast agent")
        return settings.openai_api_key.get_secret_value()

    return ChatOpenAI(
        model=settings.openai_model,
        api_key=api_key,
        use_responses_api=True,
        timeout=90,
    )


def web_search_tool(model: ChatOpenAI):
    search_model = model.bind_tools([OPENAI_WEB_SEARCH], tool_choice="required")

    @tool
    def web_search(query: str) -> str:
        """Search the web for current information and source URLs for the query."""
        return search_model.invoke(query).text

    return web_search
