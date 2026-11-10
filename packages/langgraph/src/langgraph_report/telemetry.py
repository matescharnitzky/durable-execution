from contextlib import closing, contextmanager

from langchain_core.tracers.langchain import LangChainTracer
from langsmith import Client


@contextmanager
def graph_trace(run_id: str, command: str):
    # LangGraph's callback emits graph and node spans through Logfire's OTel provider.
    with closing(Client(tracing_mode="otel", hide_inputs=True, hide_outputs=True)) as client:
        yield {
            "callbacks": [LangChainTracer(client=client)],
            "metadata": {
                "durable.runtime": "langgraph",
                "durable.run_id": run_id,
                "durable.command": command,
            },
        }
