from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from langgraph_report.config import Settings
from weather_core.prompts import WEB_SEARCH_INSTRUCTIONS


@tool
def web_search(query: str) -> dict:
    """Search the web for current information and source URLs."""
    settings = Settings()
    model = ChatOpenAI(model=settings.openai_model)
    llm_with_search = model.bind_tools([{"type": "web_search"}])
    response = llm_with_search.invoke([
        SystemMessage(WEB_SEARCH_INSTRUCTIONS), HumanMessage(query),
    ])
    sources = [
        annotation
        for block in response.content_blocks if block["type"] == "text"
        for annotation in block.get("annotations", [])
        if annotation["type"] == "citation" and annotation.get("url")
    ]
    return {"answer": response.text, "sources": sources}
