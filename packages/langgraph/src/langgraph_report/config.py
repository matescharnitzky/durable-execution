from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_ignore_empty=True)

    database_url: str = Field(
        default="postgresql://weather:weather-local@127.0.0.1:55432/weather",
        validation_alias="LANGGRAPH_DATABASE_URL",
    )
    openai_model: str = "gpt-5.4-mini"
    logfire_token: SecretStr | None = None
