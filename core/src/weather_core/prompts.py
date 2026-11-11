import json
from importlib.resources import files

_prompts = json.loads(files(__package__).joinpath("prompt.json").read_text(encoding="utf-8"))

SYSTEM_PROMPT: str = _prompts["system_prompt"]
WEB_SEARCH_INSTRUCTIONS: str = _prompts["web_search_instructions"]
