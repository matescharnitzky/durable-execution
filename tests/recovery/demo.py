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
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

FIXTURE_DATE = "2027-01-15"
FIXTURE = Path(__file__).resolve().parents[2] / "core/src/weather_core/fixtures/report.json"


def scenario(command: list[str], fault: str, worker: list[str] | None, search_tool: bool = False) -> dict:
    report = json.loads(FIXTURE.read_text())
    forecast_date = (
        (datetime.now(ZoneInfo("Europe/Budapest")).date() + timedelta(days=1)).isoformat()
        if search_tool else FIXTURE_DATE
    )
    report["forecast_date"] = forecast_date
    requests = []
    request_held = threading.Event()
    release = threading.Event()

    class Endpoint(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            assert self.path in ("/v1/responses", "/v1/chat/completions"), self.path
            completions = self.path == "/v1/chat/completions"
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            tools = body.get("tools", [])
            hosted_search = any(tool["type"] in ("web_search", "web_search_preview") for tool in tools)
            request_input = body["messages"] if completions else body["input"]
            tool_result = next(
                (item for item in request_input if item.get("type") == "function_call_output" or item.get("role") == "tool"), None
            ) if isinstance(request_input, list) else None
            if isinstance(request_input, list):
                request_input = next(item["content"] for item in request_input if item.get("role") == "user")
            if isinstance(request_input, list):
                request_input = next(part["text"] for part in request_input if part["type"] == "input_text")
            forecast = json.loads(request_input)
            assert forecast["forecast_date"] == forecast_date
            cities = forecast["cities"]
            if search_tool:
                assert cities == [row["city"] for row in report["forecasts"]]
                request_key = "step"
                if hosted_search:
                    request_number = "search"
                elif tool_result:
                    assert json.loads(tool_result["content"] if completions else tool_result["output"]) == report
                    request_number = "answer"
                else:
                    assert any(tool["type"] == "function" and (tool["function"]["name"] if completions else tool["name"]) == "web_search" for tool in tools)
                    request_number = "plan"
                result = report
                inject_fault = request_number == "answer"
            else:
                assert hosted_search
                city, = cities
                request_key = "batch"
                request_number, = (
                    i for i, row in enumerate(report["forecasts"], start=1) if row["city"] == city
                )
                result = {**report, "forecasts": [report["forecasts"][request_number - 1]]}
                inject_fault = request_number == 2
            attempt = 1 + sum(req[request_key] == request_number for req in requests)
            status = 200
            disposition = "returned"
            if inject_fault and attempt == 1:
                if fault == "crash":
                    disposition = "held"
                elif fault == "rate-limit":
                    disposition, status = "429", 429
                else:
                    disposition = "response-lost"
            requests.append({request_key: request_number, "attempt": attempt, "outcome": disposition})
            if disposition == "held":
                request_held.set()
                release.wait(120)
                return
            if disposition == "response-lost":
                self.connection.shutdown(socket.SHUT_RDWR)
                return
            message = {
                "id": "msg_fixture", "type": "message", "role": "assistant", "status": "completed",
                "content": [{"type": "output_text", "text": json.dumps(result), "annotations": []}],
            }
            if hosted_search:
                items = [
                    {"id": "ws_fixture", "type": "web_search_call", "status": "completed",
                     "action": {"type": "search", "query": f"forecast for {', '.join(cities)}"}},
                    message,
                ]
            elif request_number == "plan":
                items = [{
                    "id": "fc_fixture", "type": "function_call", "status": "completed",
                    "call_id": "call_fixture", "name": "web_search",
                    "arguments": json.dumps({"query": json.dumps(forecast)}),
                }]
            else:
                items = [message]
            response = {
                "id": f"resp_fixture_{request_number}_{attempt}",
                "object": "response",
                "created_at": 1_800_000_000,
                "model": body["model"],
                "status": "completed",
                "parallel_tool_calls": False,
                "tool_choice": "auto",
                "tools": tools,
                "usage": {"input_tokens": 100, "output_tokens": 100, "total_tokens": 200,
                          "input_tokens_details": {"cached_tokens": 0},
                          "output_tokens_details": {"reasoning_tokens": 0}},
                "output": items,
            }
            if completions:
                content = {"role": "assistant", "content": json.dumps(result)}
                if request_number == "plan":
                    content = {
                        "role": "assistant", "content": None,
                        "tool_calls": [{
                            "id": "call_fixture", "type": "function",
                            "function": {
                                "name": "web_search",
                                "arguments": json.dumps({"query": json.dumps(forecast)}),
                            },
                        }],
                    }
                response = {
                    "id": f"chatcmpl_{request_number}_{attempt}",
                    "object": "chat.completion", "created": 1_800_000_000,
                    "model": body["model"],
                    "choices": [{"index": 0, "message": content,
                                 "finish_reason": "tool_calls" if request_number == "plan" else "stop"}],
                    "usage": {"prompt_tokens": 100, "completion_tokens": 100, "total_tokens": 200},
                }
            if status == 429:
                response = {"error": {"message": "Fixture rate limit", "type": "rate_limit_error"}}
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
            args = ["run", run_id, "--fixture", "--output", str(output)]
            if not search_tool:
                args.extend(["--date", FIXTURE_DATE])
            process = subprocess.Popen([*command, *args], env=env, stdout=sys.stderr)
            if fault == "crash":
                if not request_held.wait(90):
                    raise RuntimeError(f"Worker did not reach the held request (runner exit {process.poll()})")
                stop(worker_process or process)
                stop(process)
                release.set()
                if search_tool:
                    pending = subprocess.check_output([*command, "status", run_id], env=env, timeout=30, text=True)
                    assert json.loads(pending)["next"] == ["model"], pending
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
            key, expected = ("step", ["plan", "search", "answer", "answer"]) if search_tool else ("batch", [1, 2, 2])
            assert [req[key] for req in requests] == expected, requests
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
    parser.add_argument("--search-tool", action="store_true", help="Exercise a separate search tool before the final report")
    parser.add_argument("--worker", help="Separate worker command, if needed")
    parser.add_argument("--scenario", choices=("crash", "rate-limit", "lost-response"))
    args = parser.parse_args()
    faults = [args.scenario] if args.scenario else ["crash", "rate-limit", "lost-response"]
    for fault in faults:
        worker = shlex.split(args.worker) if args.worker else None
        print(json.dumps(scenario(shlex.split(args.cli), fault, worker, args.search_tool)))


if __name__ == "__main__":
    main()
