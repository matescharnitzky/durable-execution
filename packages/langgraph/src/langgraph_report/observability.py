import os

import logfire

from langgraph_report.config import Settings


def configure_telemetry(settings: Settings) -> None:
    # Set tracing options before LangSmith creates its client on the first run.
    os.environ.pop("LANGSMITH_TRACING_MODE", None)
    os.environ.update(
        LANGSMITH_TRACING="true",
        LANGSMITH_OTEL_ENABLED="true",
        LANGSMITH_OTEL_ONLY="true",
        LANGSMITH_HIDE_INPUTS="true",
        LANGSMITH_HIDE_OUTPUTS="true",
    )

    logfire.configure(
        service_name="langgraph-report",
        send_to_logfire=settings.logfire_token is not None,
        console=False,
    )
