import os
import subprocess
import tempfile
import unittest
from pathlib import Path


class CrashScriptTest(unittest.TestCase):
    def test_status_failure_stops_polling_without_parsing_empty_output(self):
        root = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as directory:
            make = Path(directory) / "make"
            make.write_text(
                '#!/usr/bin/env bash\n'
                'if [[ "$*" == *langgraph-status* ]]; then\n'
                '  echo "Status command failed" >&2\n'
                '  exit 7\n'
                'fi\n'
                'sleep 30\n'
            )
            make.chmod(0o755)
            result = subprocess.run(
                ["bash", "tests/langgraph-crash.sh", "status-failure"], cwd=root,
                env={**os.environ, "DURABLE_ENV_LOADED": "1", "PATH": f"{directory}:{os.environ['PATH']}"},
                capture_output=True, text=True, timeout=10,
            )
        self.assertEqual(result.returncode, 7)
        self.assertIn("Status command failed", result.stderr)
        self.assertNotIn("JSONDecodeError", result.stderr)
        self.assertNotIn("Checkpoint saved", result.stdout)
