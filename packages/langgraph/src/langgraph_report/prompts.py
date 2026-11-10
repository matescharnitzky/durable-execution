from importlib.resources import files

from pydantic import BaseModel


class SearchConfig(BaseModel):
    model: str
    instructions: str


def load_search_config() -> SearchConfig:
    resource = files("weather_core").joinpath("fixtures", "search.json")
    return SearchConfig.model_validate_json(resource.read_text(encoding="utf-8"))
