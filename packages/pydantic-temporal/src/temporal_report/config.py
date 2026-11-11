from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_ignore_empty=True)

    temporal_address: str = "127.0.0.1:7233"
    temporal_task_queue: str = "durable-weather"
    openai_model: str = "gpt-5.4-mini"
    logfire_token: SecretStr | None = None
