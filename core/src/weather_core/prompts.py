import json
from importlib.resources import files

SYSTEM_PROMPT: str = json.loads(
    files(__package__).joinpath("prompt.json").read_text(encoding="utf-8")
)["system_prompt"]

WEB_SEARCH_INSTRUCTIONS = "Search public web pages for the query and cite their HTTP(S) URLs. Do not use weather widgets, internal reference IDs, or placeholder URLs as sources."
