import os

from langgraph_report.config import Settings


def configure_telemetry(settings: Settings) -> None:
    # Logfire's LangGraph integration reads these before framework imports.
    os.environ.pop("LANGSMITH_TRACING_MODE", None)
    os.environ.update(
        LANGSMITH_TRACING="true",
        LANGSMITH_OTEL_ENABLED="true",
        LANGSMITH_OTEL_ONLY="true",
        LANGSMITH_HIDE_INPUTS="true",
        LANGSMITH_HIDE_OUTPUTS="true",
    )

    import logfire

    logfire.configure(
        service_name="langgraph-report",
        send_to_logfire=settings.logfire_token is not None,
        console=False,
    )
