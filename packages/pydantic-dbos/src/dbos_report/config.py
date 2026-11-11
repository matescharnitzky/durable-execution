from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_ignore_empty=True)

    postgres_user: str = "weather"
    postgres_password: SecretStr = SecretStr("weather-local")
    postgres_db: str = "weather"
    dbos_system_database_url: str | None = None
    openai_model: str = "gpt-5.4-mini"
    logfire_token: SecretStr | None = None

    @property
    def database_url(self) -> str:
        return self.dbos_system_database_url or URL.create(
            "postgresql+psycopg", username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host="127.0.0.1", port=5432, database=self.postgres_db,
        ).render_as_string(hide_password=False)
