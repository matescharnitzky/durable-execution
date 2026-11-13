from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Load pgtask connection and model settings from the environment."""

    model_config = SettingsConfigDict(env_ignore_empty=True)
    pgtask_database_url: SecretStr = SecretStr(
        "postgresql://weather:weather-local@127.0.0.1:5432/pgtask"
    )
    openai_model: str = "gpt-6-luna"
    logfire_token: SecretStr | None = None
