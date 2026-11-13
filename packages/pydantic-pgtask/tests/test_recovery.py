import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

import pytest

from pgtask_report import commands


@pytest.mark.skipif(
    not os.getenv("PGTASK_TEST_DATABASE_URL"),
    reason="Requires a dedicated PostgreSQL test database",
)
def test_native_crash_recovery(tmp_path, monkeypatch):
    monkeypatch.setenv("PGTASK_DATABASE_URL", os.environ["PGTASK_TEST_DATABASE_URL"])
    task_id = asyncio.run(enqueue(str(uuid4())))
    worker = Path(__file__).with_name("recovery_worker.py")
    log = tmp_path / "worker.log"
    with log.open("w") as stream:
        first = subprocess.Popen(
            [sys.executable, str(worker)],
            env={**os.environ, "TEST_PHASE": "block"},
            stdout=stream,
            stderr=stream,
        )
        try:
            deadline = time.monotonic() + 30
            while "SAVED_SEARCH" not in log.read_text():
                assert first.poll() is None, log.read_text()
                assert time.monotonic() < deadline, log.read_text()
                time.sleep(0.1)
        finally:
            first.kill()
            first.wait(timeout=5)
    with log.open("a") as stream:
        second = subprocess.Popen(
            [sys.executable, str(worker)],
            env={**os.environ, "TEST_PHASE": "resume"},
            stdout=stream,
            stderr=stream,
        )
        try:
            output = tmp_path / "report.html"
            asyncio.run(asyncio.wait_for(commands.resume(task_id, output), timeout=40))
            assert "Budapest" in output.read_text()
            again = tmp_path / "again.html"
            asyncio.run(commands.resume(task_id, again))
            assert again.exists()
        finally:
            second.kill()
            second.wait(timeout=5)


async def enqueue(run_id):
    from pgtask import Client

    from pgtask_report.runtime import report

    client = await Client.connect(os.environ["PGTASK_DATABASE_URL"])
    await client.migrate()
    handle = await client.enqueue(report.request({"run_id": run_id}, idempotency_key=run_id))
    return handle.id
