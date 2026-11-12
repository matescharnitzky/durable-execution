import json
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from psycopg.errors import UndefinedColumn, UndefinedTable
from typer.testing import CliRunner

from langgraph_report.cli import app


class SavedTurnsTest(unittest.TestCase):
    def invoke(self, messages, next_nodes, *options, error=None):
        agent = MagicMock()
        agent.get_state.return_value = SimpleNamespace(
            values={"messages": messages} if messages else {}, next=next_nodes
        )
        agent.get_state.side_effect = error
        context = MagicMock()
        context.__enter__.return_value = (agent, {})
        with patch("langgraph_report.commands.langgraph_agent", return_value=context):
            result = CliRunner().invoke(app, ["status", "example", *options])
        self.assertEqual(result.exit_code, 0, result.output)
        return result.output

    def test_table_shows_saved_messages_and_tool_calls(self):
        messages = [
            HumanMessage("Generate the weather report."),
            AIMessage(
                "",
                tool_calls=[
                    {"name": "web_search", "args": {"query": "tomorrow Budapest"}, "id": "search-1"}
                ],
            ),
            ToolMessage("[bold]Sunny[/bold]", tool_call_id="search-1", name="web_search"),
        ]
        output = self.invoke(messages, ("model",))
        for text in (
            "pending",
            "model",
            "User",
            "Model",
            "Tool",
            "web_search",
            "tomorrow",
            "Budapest",
            "[bold]Sunny[/bold]",
        ):
            self.assertIn(text, output)

    def test_json_remains_machine_readable_for_readiness_polling(self):
        output = self.invoke([HumanMessage("Generate the weather report.")], ("model",), "--json")
        self.assertEqual(
            json.loads(output), {"run_id": "example", "state": "pending", "next": ["model"]}
        )

    def test_unknown_run_has_no_saved_turns(self):
        output = self.invoke([], ())
        self.assertIn("unknown", output)
        self.assertIn("No saved turns.", output)

    def test_status_during_checkpoint_setup_returns_unknown(self):
        for error in (UndefinedTable, UndefinedColumn):
            with self.subTest(error=error.__name__):
                output = self.invoke(
                    [], (), "--json", error=error("Checkpoint schema is not ready")
                )
                self.assertEqual(
                    json.loads(output), {"run_id": "example", "state": "unknown", "next": []}
                )
