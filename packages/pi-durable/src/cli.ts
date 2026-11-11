import { spawnSync } from "node:child_process";
import { mkdir, open, stat } from "node:fs/promises";
import { join } from "node:path";
import { Command, Option } from "commander";
import { BACKGROUND_CONTEXT as context } from "@earendil-works/chord/context";
import { createRegistry, defineExtension, Harness } from "@earendil-works/pi-durable";
import { openNodeSqliteStorage } from "@earendil-works/pi-durable/storage/sqlite/node";

import { settings, systemPrompt } from "./config.ts";
import { openaiModels, modelRef } from "./provider.ts";
import { webSearch } from "./tools.ts";
import { logfireTelemetry } from "./telemetry.ts";

const requestId = "weather-report";

export async function report(command: string, runId: string, options: { output?: string; json?: boolean }) {
  if (!/^[a-zA-Z0-9_-]+$/.test(runId)) throw new Error("Use a run ID containing letters, numbers, underscores, or dashes");
  const database = join(settings.stateDirectory, `${runId}.sqlite`);
  const exists = await stat(database).then(() => true, error => {
    if (error.code === "ENOENT") return false;
    throw error;
  });
  if (!exists && command === "status") {
    console.log(options.json ? JSON.stringify({ run_id: runId, state: "unknown" }) : "Unknown run ID.");
    return;
  }
  if (!exists && command === "resume") throw new Error("Unknown run ID");
  if (command === "run") {
    await mkdir(settings.stateDirectory, { recursive: true });
    await (await open(database, "wx", 0o600)).close();
  }
  const telemetry = command === "status" ? undefined : logfireTelemetry(runId);
  const storage = await openNodeSqliteStorage(database);
  const registry = createRegistry();
  registry.install(defineExtension({ name: "weather", tools: [webSearch] }));
  const harness = await Harness.open(storage, {
    models: openaiModels(), registry, settings: { toolExecution: "sequential" },
    readOnly: command === "status", telemetry: telemetry?.context,
  }, context);
  try {
    const stored = (await storage.scanSubmissions({}, 100, undefined, context)).items.find(item => item.requestId === requestId);
    if (command === "status") {
      const state = !stored ? "unknown" : stored.status === "done" ? "complete" : stored.status === "unanswered" ? "failed" : "pending";
      if (options.json) {
        console.log(JSON.stringify({ run_id: runId, state, submission_id: stored?.id, submission_status: stored?.status, reason: stored?.status === "unanswered" ? stored.reason : undefined }));
        return;
      }
      console.log(`Run: ${runId}\nState: ${state} · Submission: ${stored?.status || "none"}`);
      if (stored?.status === "unanswered" && typeof stored.detail === "string") console.log(stored.detail);
      if (!stored) return;
      const conversation = await harness.conversation(stored.conversationId, context);
      const entries = await conversation!.entries({}, 100, undefined, context);
      console.log("Latest 100 committed history entries:");
      const messages = entries.items.toReversed().flatMap(entry => entry.model || []);
      console.table(messages.filter(message => message.role !== "system").map((message, index) => ({
        Turn: index + 1,
        Role: message.role,
        "Saved content": (typeof message.content === "string" ? message.content : message.content.map(part =>
          part.type === "text" ? part.text : part.type === "toolCall" ? `${part.name}(${JSON.stringify(part.arguments)})` : ""
        ).join(" ")).replace(/\s+/g, " ").slice(0, 240),
      })));
      return;
    }
    const submission = command === "run"
      ? await (await harness.root(context, { agent: { model: modelRef, instructions: systemPrompt } })).submit({
        type: "input", content: "Generate the weather report.", requestId,
      }, context)
      : stored ? await harness.submission(stored.id, context) : undefined;
    if (!submission) throw new Error("No durable submission exists for this run");
    harness.resume();
    const settled = await submission.wait(context);
    if (settled.status !== "done" || settled.type !== "input") {
      const detail = settled.status === "unanswered" && typeof settled.detail === "string" ? `: ${settled.detail}` : "";
      throw new Error(`Pi submission ended as ${settled.status}${detail}`);
    }
    const answer = await storage.entry(settled.conversationId, settled.answer, context);
    const message = answer?.entry.model?.find(message => message.role === "assistant");
    if (!message || message.role !== "assistant") throw new Error("No saved final report");
    const text = message.content.filter(part => part.type === "text").map(part => part.text).join("");
    const args = ["run", "--locked", "--package", "weather-core", "weather-report", "Pi"];
    if (options.output) args.push("--output", options.output);
    const rendered = spawnSync("uv", args, { input: text.trim().replace(/^```json\s*|\s*```$/g, ""), encoding: "utf8" });
    if (rendered.status !== 0) throw new Error(rendered.stderr || "Shared report renderer failed");
    console.error(`Report saved to ${rendered.stdout.trim()}`);
  } finally {
    await harness.close(context);
    await telemetry?.close();
  }
}

const program = new Command().name("pi-report");
for (const command of ["run", "status", "resume"]) {
  const action = program.command(command).argument("<run-id>");
  if (command === "status") action.addOption(new Option("--json", "Return machine-readable status"));
  else action.option("--output <path>", "Override the report filename");
  action.action(async (runId: string, options) => { await report(command, runId, options); });
}
try {
  await program.parseAsync();
} catch (error) {
  console.error(error instanceof Error ? error.message : "Pi report failed");
  process.exitCode = 1;
}
