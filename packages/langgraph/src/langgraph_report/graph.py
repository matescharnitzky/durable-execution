import json

from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import AgentMiddleware, ModelRetryMiddleware, hook_config
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.postgres import PostgresSaver
from openai import APIConnectionError, InternalServerError, RateLimitError

from langgraph_report.config import SEARCH, Settings
from langgraph_report.report import validate_batch
from langgraph_report.tools import WEB_SEARCH, forecast_model


class ReportState(AgentState):
    forecast_date: str
    batches: list[list[str]]
    results: list[dict]


class ForecastBatches(AgentMiddleware):
    """Give each batch its own checkpointed turn within the same agent run."""

    def wrap_model_call(self, request, handler):
        state = request.state
        cities = state["batches"][len(state["results"])]
        prompt = HumanMessage(json.dumps({"forecast_date": state["forecast_date"], "cities": cities}))
        return handler(request.override(messages=[prompt], tool_choice="required"))

    @hook_config(can_jump_to=["model", "end"])
    def after_model(self, state: ReportState, runtime) -> dict:
        index = len(state["results"])
        text = state["messages"][-1].text.strip().removeprefix("```json").removesuffix("```").strip()
        result = validate_batch(json.loads(text), state["forecast_date"], state["batches"][index])
        return {
            "results": [*state["results"], result],
            "jump_to": "model" if index + 1 < len(state["batches"]) else "end",
        }


def build_agent(checkpointer: PostgresSaver, settings: Settings):
    return create_agent(
        model=forecast_model(settings),
        tools=[WEB_SEARCH],
        system_prompt=SEARCH["instructions"],
        state_schema=ReportState,
        middleware=[
            ForecastBatches(),
            ModelRetryMiddleware(
                max_retries=2,
                retry_on=(APIConnectionError, InternalServerError, RateLimitError),
                on_failure="error",
            ),
        ],
        checkpointer=checkpointer,
        name="Weather report",
    )
