"""Exercise a runtime CLI using a fixture endpoint that never supplies recovery state."""

import argparse
import json
import os
import shlex
import socket
import subprocess
import sys
import tempfile
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

FIXTURE_DATE = "2027-01-15"
FIXTURE = Path(__file__).resolve().parents[2] / "core/src/weather_core/fixtures/report.json"


def scenario(command: list[str], fault: str, worker: list[str] | None) -> dict:
    report = json.loads(FIXTURE.read_text())
    requests = []
    batch_b = threading.Event()
    release = threading.Event()

    class Endpoint(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            assert self.path == "/v1/responses", self.path
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            assert any(tool["type"] in ("web_search", "web_search_preview") for tool in body["tools"])
            request_input = body["input"]
            if isinstance(request_input, list):
                request_input = next(item["content"] for item in request_input if item.get("role") == "user")
            if isinstance(request_input, list):
                request_input = next(part["text"] for part in request_input if part["type"] == "input_text")
            forecast = json.loads(request_input)
            assert forecast["forecast_date"] == FIXTURE_DATE
            city, = forecast["cities"]
            city_number = next(i for i, row in enumerate(report["forecasts"]) if row["city"] == city)
            attempt = 1 + sum(req["batch"] == city_number + 1 for req in requests)
            status = 200
            disposition = "returned"
            if city_number == 1 and attempt == 1:
                if fault == "crash":
                    disposition = "held"
                elif fault == "rate-limit":
                    disposition, status = "429", 429
                else:
                    disposition = "response-lost"
            requests.append({"batch": city_number + 1, "attempt": attempt, "outcome": disposition})
            if disposition == "held":
                batch_b.set()
                release.wait(120)
                return
            result = {**report, "forecasts": [report["forecasts"][city_number]]}
            if disposition == "response-lost":
                self.connection.shutdown(socket.SHUT_RDWR)
                return
            response = {
                "id": f"resp_fixture_{city_number}_{attempt}",
                "object": "response",
                "created_at": 1_800_000_000,
                "model": body["model"],
                "status": "completed",
                "parallel_tool_calls": False,
                "tool_choice": "auto",
                "tools": body["tools"],
                "usage": {"input_tokens": 100, "output_tokens": 100, "total_tokens": 200,
                          "input_tokens_details": {"cached_tokens": 0},
                          "output_tokens_details": {"reasoning_tokens": 0}},
                "output": [
                    {"id": "ws_fixture", "type": "web_search_call", "status": "completed",
                     "action": {"type": "search", "query": f"forecast for {city}"}},
                    {"id": "msg_fixture", "type": "message", "role": "assistant", "status": "completed",
                     "content": [{"type": "output_text", "text": json.dumps(result), "annotations": []}]},
                ],
            }
            if status == 429:
                response = {"error": {"message": "Fixture rate limit", "type": "rate_limit_error"}}
            if status == 200 and body.get("stream"):
                message = response["output"][1]
                events = [
                    {"type": "response.created", "response": response},
                    {"type": "response.output_item.added", "output_index": 1,
                     "item": {**message, "status": "in_progress", "content": []}},
                    {"type": "response.output_item.done", "output_index": 1, "item": message},
                    {"type": "response.completed", "response": response},
                ]
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                for index, event in enumerate(events):
                    event["sequence_number"] = index
                    self.wfile.write(f'event: {event["type"]}\ndata: {json.dumps(event)}\n\n'.encode())
                return
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

    def stop(process):
        if process and process.poll() is None:
            process.kill()
            process.wait(timeout=10)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Endpoint)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    env = os.environ | {
        "OPENAI_BASE_URL": f"http://127.0.0.1:{server.server_port}/v1",
        "OPENAI_API_KEY": "fixture",
        "DURABLE_FIXTURE": "1",
        "LOGFIRE_TOKEN": "",
    }
    run_id = f"demo-{fault}-{uuid.uuid4().hex}"
    process = worker_process = None
    try:
        with tempfile.TemporaryDirectory() as directory:
            env["PI_STATE_DIR"] = directory
            output = Path(directory) / "weather.html"
            if worker:
                worker_process = subprocess.Popen(worker, env=env)
            args = ["run", run_id, "--date", FIXTURE_DATE, "--fixture", "--output", str(output)]
            process = subprocess.Popen([*command, *args], env=env, stdout=sys.stderr)
            if fault == "crash":
                if not batch_b.wait(90):
                    raise RuntimeError(f"Worker did not reach batch B (runner exit {process.poll()})")
                stop(worker_process or process)
                stop(process)
                release.set()
                if worker:
                    worker_process = subprocess.Popen(worker, env=env)
                subprocess.run(
                    [*command, "resume", run_id, "--output", str(output)],
                    env=env, check=True, timeout=120, stdout=sys.stderr,
                )
            elif process.wait(timeout=120):
                raise RuntimeError(f"Runner exited with status {process.returncode}")
            html = output.read_text()
            for forecast in report["forecasts"]:
                assert forecast["city"] in html and forecast["sources"][0]["url"] in html
            status = subprocess.check_output([*command, "status", run_id], env=env, timeout=30, text=True)
            assert json.loads(status)["state"] == "complete", status
            assert [req["batch"] for req in requests] == [1, 2, 2], requests
            return {"scenario": fault, "run_id": run_id, "requests": requests, "native_status": json.loads(status)}
    finally:
        stop(process)
        stop(worker_process)
        release.set()
        server.shutdown()
        server.server_close()
        thread.join()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("cli", help="Runtime CLI command, including any wrapper")
    parser.add_argument("--worker", help="Separate worker command, if needed")
    parser.add_argument("--scenario", choices=("crash", "rate-limit", "lost-response"))
    args = parser.parse_args()
    faults = [args.scenario] if args.scenario else ["crash", "rate-limit", "lost-response"]
    for fault in faults:
        print(json.dumps(scenario(shlex.split(args.cli), fault, shlex.split(args.worker) if args.worker else None)))


if __name__ == "__main__":
    main()
