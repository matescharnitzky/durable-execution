import unittest
from unittest.mock import patch

from langchain_core.messages import AIMessage

from langgraph_report.tools import web_search


class SearchSourcesTest(unittest.TestCase):
    def test_provider_citations_reach_the_agent_even_when_text_omits_urls(self):
        response = AIMessage(
            content=[
                {
                    "type": "text",
                    "text": "Cloudy",
                    "annotations": [
                        {
                            "type": "url_citation",
                            "url": "https://example.com/forecast",
                            "title": "Test source",
                            "start_index": 0,
                            "end_index": 6,
                        }
                    ],
                }
            ],
            response_metadata={"model_provider": "openai"},
        )
        with patch("langgraph_report.tools.ChatOpenAI") as model:
            model.return_value.bind_tools.return_value.invoke.return_value = response
            result = web_search.invoke({"query": "tomorrow Budapest"})
        self.assertEqual(result["answer"], "Cloudy")
        self.assertEqual(result["sources"][0]["url"], "https://example.com/forecast")
