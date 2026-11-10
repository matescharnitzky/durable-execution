from langchain.agents import create_agent
from langgraph.checkpoint.postgres import PostgresSaver

from langgraph_report.config import SEARCH, Settings
from langgraph_report.tools import OPENAI_WEB_SEARCH, forecast_model


def build_agent(checkpointer: PostgresSaver, settings: Settings):
    return create_agent(
        model=forecast_model(settings),
        tools=[OPENAI_WEB_SEARCH],
        system_prompt=SEARCH["instructions"],
        checkpointer=checkpointer,
        name="Weather report",
    )
