import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from pydantic_ai.durable_exec.temporal import LogfirePlugin, PydanticAIPlugin
from typer.testing import CliRunner

from temporal_report.cli import app


class TemporalRuntimeTest(unittest.TestCase):
    def test_worker_is_constructed_on_the_running_sdk_loop(self):
        worker = MagicMock()
        worker.run = AsyncMock()

        def construct_worker(*args, **kwargs):
            self.assertTrue(asyncio.get_running_loop().is_running())
            return worker

        with patch("temporal_report.cli.Client.connect", new=AsyncMock()), patch(
            "temporal_report.cli.Worker", side_effect=construct_worker
        ), patch("temporal_report.cli.logfire.force_flush"):
            result = CliRunner().invoke(app, ["worker"])
        self.assertEqual(result.exit_code, 0, result.output)
        worker.run.assert_awaited_once()

    def test_runtime_closes_its_loop_and_flushes_after_a_command_fails(self):
        client = MagicMock()
        loops = []

        async def fail_start(*args, **kwargs):
            loops.append(asyncio.get_running_loop())
            raise ValueError("Command failed")

        client.start_workflow = AsyncMock(side_effect=fail_start)
        with patch("temporal_report.cli.Client.connect", new=AsyncMock(return_value=client)), patch(
            "temporal_report.cli.logfire.force_flush"
        ) as flush:
            result = CliRunner().invoke(app, ["run", "example"])
        self.assertIsInstance(result.exception, ValueError)
        self.assertEqual(str(result.exception), "Command failed")
        self.assertEqual(len(loops), 1)
        self.assertTrue(loops[0].is_closed())
        flush.assert_called_once()

    def test_run_and_resume_export_the_native_workflow_result(self):
        fixture = Path(__file__).resolve().parents[3] / "core/tests/report.json"
        handle = MagicMock()
        handle.result = AsyncMock(return_value=json.loads(fixture.read_text()))
        client = MagicMock()
        client.start_workflow = AsyncMock(return_value=handle)
        client.get_workflow_handle.return_value = handle
        with tempfile.TemporaryDirectory() as directory, patch(
            "temporal_report.cli.Client.connect", new=AsyncMock(return_value=client)
        ) as connect, patch("temporal_report.cli.logfire.force_flush"):
            for command in ("run", "resume"):
                output = Path(directory) / f"{command}.html"
                result = CliRunner().invoke(app, [command, "example", "--output", str(output)])
                self.assertEqual(result.exit_code, 0, result.output)
                self.assertIn("Weather forecast", output.read_text())
                plugins = connect.call_args.kwargs["plugins"]
                self.assertIsInstance(plugins[0], PydanticAIPlugin)
                self.assertIsInstance(plugins[1], LogfirePlugin)
                self.assertFalse(plugins[1].metrics)
                self.assertNotIn("interceptors", connect.call_args.kwargs)
        client.start_workflow.assert_awaited_once()
        client.get_workflow_handle.assert_called_once_with("example")
        self.assertEqual(handle.result.await_count, 2)

    def test_status_awaits_history_on_the_connected_client_loop(self):
        client = MagicMock()
        handle = MagicMock()
        handle.describe = AsyncMock()
        handle.describe.return_value.status.name = "RUNNING"
        handle.describe.return_value.raw_description.pending_activities = []
        handle.fetch_history = AsyncMock()
        handle.fetch_history.return_value.events = []
        client.get_workflow_handle.return_value = handle
        loops = []

        async def connect(*args, **kwargs):
            loops.append(asyncio.get_running_loop())
            return client

        async def describe():
            self.assertIs(asyncio.get_running_loop(), loops[0])
            return handle.describe.return_value

        handle.describe.side_effect = describe
        with patch("temporal_report.cli.Client.connect", new=AsyncMock(side_effect=connect)), patch(
            "temporal_report.cli.logfire.force_flush"
        ) as flush:
            result = CliRunner().invoke(app, ["status", "example", "--json"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(json.loads(result.output)["state"], "pending")
        handle.fetch_history.assert_awaited_once()
        self.assertTrue(loops[0].is_closed())
        flush.assert_called_once()
