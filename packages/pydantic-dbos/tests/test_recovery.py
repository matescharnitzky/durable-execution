import os
import select
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


class DurableSearchTest(unittest.TestCase):
    def test_completed_search_is_replayed_after_worker_is_killed(self):
        worker = Path(__file__).with_name("recovery_worker.py")
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "dbos.sqlite"
            env = {**os.environ, "DBOS_TEST_DATABASE_URL": f"sqlite:///{database}", "PYDANTIC_AI_NO_BANNER": "1"}
            process = subprocess.Popen(
                [sys.executable, str(worker)], env={**env, "DBOS_TEST_PHASE": "block"},
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            try:
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    if select.select([process.stdout], [], [], 0.2)[0]:
                        if process.stdout.readline().strip() == "MODEL_WAITING_AFTER_SAVED_SEARCH":
                            break
                    if process.poll() is not None:
                        self.fail(process.stderr.read())
                else:
                    self.fail("Worker did not reach the model turn after the saved search")
                process.kill()
                process.wait(timeout=5)
                with sqlite3.connect(database) as connection:
                    steps = connection.execute(
                        "SELECT function_name FROM operation_outputs WHERE workflow_uuid = ? ORDER BY function_id",
                        ("search-replay",),
                    ).fetchall()
                self.assertEqual([name for (name,) in steps], ["dbos_replay_test__model.request", "web_search"])
                resumed = subprocess.run(
                    [sys.executable, str(worker)], env={**env, "DBOS_TEST_PHASE": "resume"},
                    capture_output=True, text=True, timeout=20,
                )
                self.assertEqual(resumed.returncode, 0, resumed.stderr)
                self.assertIn("REPORT_COMPLETED_WITH_SAVED_SEARCH", resumed.stdout)
            finally:
                if process.poll() is None:
                    process.kill()
                process.communicate(timeout=5)
