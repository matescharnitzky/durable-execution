from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from langgraph_report.prompts import load_search_config


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_ignore_empty=True)

    database_url: str = Field(
        default="postgresql://weather:weather-local@127.0.0.1:55432/weather",
        validation_alias="LANGGRAPH_DATABASE_URL",
    )
    openai_model: str = Field(default_factory=lambda: load_search_config().model)
    openai_api_key: SecretStr | None = None
    logfire_token: SecretStr | None = None
