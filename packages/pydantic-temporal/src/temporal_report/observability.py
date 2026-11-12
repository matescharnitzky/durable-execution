import logfire

from temporal_report.config import Settings


def configure_telemetry() -> logfire.Logfire:
    """Configure Logfire and Pydantic AI tracing with content disabled."""
    settings = Settings()
    instance = logfire.configure(
        service_name="temporal-report",
        send_to_logfire=settings.logfire_token is not None,
        console=False,
    )
    instance.instrument_pydantic_ai(include_content=False)
    return instance
