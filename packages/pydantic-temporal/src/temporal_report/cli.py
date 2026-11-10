import asyncio
import json
import os

import logfire
from pydantic_ai.durable_exec.temporal import PydanticAIPlugin
from temporalio import activity
from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy
from temporalio.service import RPCError, RPCStatusCode
from temporalio.worker import ActivityInboundInterceptor, Interceptor, Worker

from temporal_report.workflow import WeatherReport

from pydantic_report.report import arguments, batches, write_report

TASK_QUEUE = "durable-weather"


async def connect():
    return await Client.connect(os.getenv("TEMPORAL_ADDRESS") or "127.0.0.1:7233", plugins=[PydanticAIPlugin()])


async def inspect(handle, run_id):
    try:
        description = await handle.describe()
    except RPCError as error:
        if error.status != RPCStatusCode.NOT_FOUND:
            raise
        return {"run_id": run_id, "state": "unknown"}
    native = description.status.name
    history = await handle.fetch_history()
    return {
        "run_id": run_id,
        "state": {"RUNNING": "pending", "COMPLETED": "complete"}.get(native, "failed"),
        "workflow_status": native,
        "activities": [
            {
                "scheduled_event": event.activity_task_started_event_attributes.scheduled_event_id,
                "attempt": event.activity_task_started_event_attributes.attempt,
            }
            for event in history.events
            if event.HasField("activity_task_started_event_attributes")
        ],
    }


async def run_cli(args):
    client = await connect()
    handle = client.get_workflow_handle(args.run_id)
    if args.command == "status":
        print(json.dumps(await inspect(handle, args.run_id)))
        return
    with logfire.span(
        "Temporal {command}", command=args.command,
        **{"durable.runtime": "temporal", "durable.run_id": args.run_id},
    ):
        if args.command == "run":
            handle = await client.start_workflow(
                WeatherReport.run,
                args=[args.run_id, args.date.isoformat(), batches(args.fixture)],
                id=args.run_id,
                task_queue=TASK_QUEUE,
                id_reuse_policy=WorkflowIDReusePolicy.REJECT_DUPLICATE,
            )
        write_report(args.output, await handle.result())


def main():
    args = arguments("temporal")
    logfire.configure(service_name="temporal-report", send_to_logfire=bool(os.getenv("LOGFIRE_TOKEN")), console=False)
    asyncio.run(run_cli(args))


class ActivityTelemetry(ActivityInboundInterceptor):
    async def execute_activity(self, input):
        info = activity.info()
        with logfire.span(
            "Temporal activity {activity_type}", activity_type=info.activity_type,
            **{
                "durable.runtime": "temporal",
                "durable.run_id": info.workflow_id,
                "durable.attempt": info.attempt,
            },
        ):
            return await super().execute_activity(input)


class WorkerTelemetry(Interceptor):
    def intercept_activity(self, next):
        return ActivityTelemetry(next)


async def run_worker():
    client = await connect()
    await Worker(
        client, task_queue=TASK_QUEUE, workflows=[WeatherReport], interceptors=[WorkerTelemetry()],
    ).run()


def worker():
    logfire.configure(service_name="temporal-report", send_to_logfire=bool(os.getenv("LOGFIRE_TOKEN")), console=False)
    asyncio.run(run_worker())
