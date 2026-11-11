from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from langgraph_report.config import Settings


@tool
def web_search(query: str) -> str:
    """Search the web for current information and source URLs."""
    settings = Settings()
    model = ChatOpenAI(model=settings.openai_model)
    llm_with_search = model.bind_tools([{"type": "web_search"}])
    return llm_with_search.invoke(query).text
