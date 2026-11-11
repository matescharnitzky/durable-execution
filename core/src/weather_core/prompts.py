import json
from importlib.resources import files

SYSTEM_PROMPT: str = json.loads(
    files(__package__).joinpath("prompt.json").read_text(encoding="utf-8")
)["system_prompt"]
