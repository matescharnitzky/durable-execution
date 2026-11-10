import { mkdir, open, stat } from "node:fs/promises";
import { join } from "node:path";
import { parseArgs } from "node:util";
import { BACKGROUND_CONTEXT as context } from "@earendil-works/chord/context";
import { AssistantEntry, createRegistry, Harness } from "@earendil-works/pi-durable";
import { openNodeSqliteStorage } from "@earendil-works/pi-durable/storage/sqlite/node";

import { forecastModels, modelRef } from "./provider.ts";
import { cityBatches, validateBatch, writeReport, type BatchInput, type BatchReport } from "./report.ts";
import { logfireTelemetry } from "./telemetry.ts";

async function main() {
  const { positionals, values } = parseArgs({
    allowPositionals: true,
    options: { date: { type: "string" }, output: { type: "string" }, fixture: { type: "boolean" } },
  });
  const [command, runId] = positionals;
  if (positionals.length !== 2 || !["run", "resume", "status"].includes(command) || !/^[a-zA-Z0-9_-]+$/.test(runId)) {
    throw new Error("Usage: pi-report (run|status|resume) RUN_ID [--date YYYY-MM-DD] [--output PATH] [--fixture]");
  }
  if (command !== "status" && !values.output) throw new Error("--output is required");
  if (command === "run" && (
    !values.date || !/^\d{4}-\d{2}-\d{2}$/.test(values.date)
    || new Date(values.date).toISOString().slice(0, 10) !== values.date
  )) throw new Error("Use an explicit valid --date YYYY-MM-DD");

  const directory = process.env.PI_STATE_DIR || "artifacts/pi";
  const database = join(directory, `${runId}.sqlite`);
  const exists = await stat(database).then(() => true, error => {
    if (error.code === "ENOENT") return false;
    throw error;
  });
  if (command === "status" && !exists) {
    console.log(JSON.stringify({ run_id: runId, state: "unknown" }));
    return;
  }
  if (command === "resume" && !exists) throw new Error("Unknown run ID");
  if (command === "run") {
    await mkdir(directory, { recursive: true });
    await (await open(database, "wx", 0o600)).close();
  }

  const telemetry = logfireTelemetry(runId);
  const harness = await Harness.open(await openNodeSqliteStorage(database), {
    models: forecastModels(),
    registry: createRegistry(),
    readOnly: command === "status",
    settings: { retry: { enabled: true, maxRetries: 2, baseDelayMs: 500 } },
    telemetry: telemetry?.context,
  }, context);
  try {
    const root = command === "run" ? await harness.root(context, { agent: { model: modelRef } })
      : await harness.root(context);
    const view = await root.context(context);
    const initial = view.messages.find(message => message.role === "user");
    if (command === "status") {
      const turns = view.entries.filter(entry => entry.kind === "pi.assistant").map(entry => ({
        entry: entry.id,
        task: entry.byTaskId,
        outcome: entry.model?.find(message => message.role === "assistant")?.stopReason,
      }));
      const expected = typeof initial?.content === "string"
        ? (JSON.parse(initial.content) as BatchInput).city_batches.length : undefined;
      const completed = turns.filter(turn => turn.outcome === "stop").length;
      const state = expected === undefined ? "unknown" : completed === expected ? "complete" : "pending";
      console.log(JSON.stringify({ run_id: runId, state, completed_batches: completed, turns }));
      return;
    }
    const first: BatchInput = command === "run"
      ? { forecast_date: values.date!, city_batches: cityBatches(values.fixture ?? false), batch: 1 }
      : typeof initial?.content === "string" ? JSON.parse(initial.content) as BatchInput
      : (() => { throw new Error("No durable submission exists for this run"); })();

    harness.resume();
    const results: BatchReport[] = [];
    for (let index = 0; index < first.city_batches.length; index++) {
      const input = { ...first, batch: index + 1 };
      const submission = await root.submit({
        type: "input", content: JSON.stringify(input), requestId: `batch-${input.batch}`,
      }, context);
      const settled = await submission.wait(context);
      if (settled.status !== "done" || settled.type !== "input") {
        throw new Error(`Pi submission ${submission.id} did not complete`);
      }
      const entry = await root.commit(tx => tx.entry(AssistantEntry, settled.answer), context);
      const message = entry?.model?.find(part => part.role === "assistant");
      const text = message?.content.find(part => part.type === "text");
      if (!text) throw new Error(`Pi submission ${submission.id} has no forecast`);
      results.push(validateBatch(JSON.parse(text.text.trim().replace(/^```json\s*|\s*```$/g, "")), input));
    }
    await writeReport(values.output!, results);
  } finally {
    await harness.close(context);
    await telemetry?.close();
  }
}

try {
  await main();
} catch (error) {
  console.error(error instanceof Error ? error.message : "Pi report failed");
  process.exitCode = 1;
}
