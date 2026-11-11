from psycopg.conninfo import make_conninfo
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_ignore_empty=True)

    postgres_user: str = "weather"
    postgres_password: SecretStr = SecretStr("weather-local")
    postgres_db: str = "weather"
    langgraph_database_url: str | None = None
    openai_model: str = "gpt-5.4-mini"
    logfire_token: SecretStr | None = None

    @property
    def database_url(self) -> str:
        connection = self.langgraph_database_url or make_conninfo(
            host="127.0.0.1",
            port=5432,
            dbname=self.postgres_db,
            user=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
        )
        return make_conninfo(connection, options="-c search_path=langgraph")
