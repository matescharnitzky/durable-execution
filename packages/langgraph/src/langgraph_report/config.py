import json
import os
from importlib.resources import files

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

SEARCH = json.loads(
    files("weather_core").joinpath("fixtures", "search.json").read_text(encoding="utf-8")
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_ignore_empty=True)

    database_url: str = Field(
        default="postgresql://weather:weather-local@127.0.0.1:55432/weather",
        validation_alias="LANGGRAPH_DATABASE_URL",
    )
    openai_model: str = SEARCH["model"]
    openai_api_key: SecretStr | None = None
    logfire_token: SecretStr | None = None


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
