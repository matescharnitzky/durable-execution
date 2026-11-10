import json
import os

import logfire
from dbos import DBOS, DBOSClient, SetWorkflowID
from pydantic_ai.durable_exec.dbos import DBOSDurability

from dbos_report.agent import forecast_batches, report_agent

from dbos_report.report import arguments, batches, write_report


def main():
    args = arguments("dbos")
    logfire.configure(service_name="dbos-report", send_to_logfire=bool(os.getenv("LOGFIRE_TOKEN")), console=False)
    database = os.getenv("DBOS_SYSTEM_DATABASE_URL") or (
        "postgresql://weather:weather-local@127.0.0.1:55432/weather_dbos"
    )
    if args.command == "status":
        client = DBOSClient(system_database_url=database)
        try:
            statuses = client.list_workflows(workflow_ids=[args.run_id], load_input=False, load_output=False)
            native = statuses[0].status if statuses else "UNKNOWN"
            steps = client.list_workflow_steps(args.run_id, load_output=False) if statuses else []
            print(json.dumps({
                "run_id": args.run_id,
                "state": {"SUCCESS": "complete", "UNKNOWN": "unknown", "ERROR": "failed"}.get(native, "pending"),
                "workflow_status": native,
                "steps": [step["function_name"] for step in steps],
            }))
        finally:
            client.destroy()
        return

    DBOS(config={"name": "weather-report", "system_database_url": database})
    agent = report_agent(DBOSDurability(model_step_config={
        "retries_allowed": True, "max_attempts": 3, "interval_seconds": 1.0,
    }))

    @DBOS.workflow()
    async def report(run_id: str, forecast_date: str, city_batches: list[list[str]]) -> list[dict]:
        with logfire.span("DBOS report", **{"durable.runtime": "dbos", "durable.run_id": run_id}):
            return await forecast_batches(agent, run_id, forecast_date, city_batches)

    DBOS.launch()
    try:
        with logfire.span(
            "DBOS {command}", command=args.command,
            **{"durable.runtime": "dbos", "durable.run_id": args.run_id},
        ):
            if args.command == "run":
                if DBOS.get_workflow_status(args.run_id):
                    raise SystemExit("Run ID already exists. Use resume.")
                with SetWorkflowID(args.run_id):
                    handle = DBOS.start_workflow(report, args.run_id, args.date.isoformat(), batches(args.fixture))
            else:
                handle = DBOS.retrieve_workflow(args.run_id)
            write_report(args.output, handle.get_result())
    finally:
        DBOS.destroy()
