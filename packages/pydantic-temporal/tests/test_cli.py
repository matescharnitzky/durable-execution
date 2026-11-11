import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from pydantic_ai.durable_exec.temporal import LogfirePlugin, PydanticAIPlugin
from typer.testing import CliRunner

from temporal_report.cli import app, temporal_runtime


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
        with patch("temporal_report.cli.Client.connect", new=AsyncMock(return_value=client)), patch(
            "temporal_report.cli.logfire.force_flush"
        ) as flush:
            with self.assertRaisesRegex(ValueError, "Command failed"):
                with temporal_runtime() as (connected, runner):
                    self.assertIs(connected, client)
                    loop = runner.get_loop()
                    raise ValueError("Command failed")
            self.assertTrue(loop.is_closed())
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
                self.assertNotIn("interceptors", connect.call_args.kwargs)
        client.start_workflow.assert_awaited_once()
        client.get_workflow_handle.assert_called_once_with("example")
        self.assertEqual(handle.result.await_count, 2)
