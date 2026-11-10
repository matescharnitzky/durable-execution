from langchain.agents import create_agent
from langgraph.checkpoint.postgres import PostgresSaver

from langgraph_report.config import SEARCH, Settings
from langgraph_report.tools import forecast_model, web_search_tool


def build_agent(checkpointer: PostgresSaver, settings: Settings):
    model = forecast_model(settings)
    return create_agent(
        model=model,
        tools=[web_search_tool(model)],
        system_prompt=(
            "Call web_search to collect forecasts and source URLs before writing the report. "
            + SEARCH["instructions"]
        ),
        checkpointer=checkpointer,
        name="Weather report",
    )
