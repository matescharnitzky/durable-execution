import json
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
