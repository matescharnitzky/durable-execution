import assert from "node:assert/strict";
import { spawn, spawnSync } from "node:child_process";
import { once } from "node:events";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

const cli = new URL("../src/cli.ts", import.meta.url).pathname;
const provider = new URL("./provider.mjs", import.meta.url).pathname;
const args = ["--experimental-test-module-mocks", "--import", provider, cli];

test("Pi reopens a killed submission, resumes it, and exports through core", { timeout: 30000 }, async () => {
  const directory = await mkdtemp(join(tmpdir(), "pi-recovery-"));
  const env = { ...process.env, OPENAI_API_KEY: "fixture", OPENAI_MODEL: "gpt-5.4-mini", LOGFIRE_TOKEN: "", PI_TEST_BLOCK: "", PI_STATE_DIR: join(directory, "state") };
  const worker = spawn(process.execPath, [...args, "run", "offline-crash"], {
    env: { ...env, PI_TEST_BLOCK: "1" }, stdio: ["ignore", "pipe", "pipe"],
  });
  let errors = "";
  worker.stderr.on("data", chunk => { errors += chunk; });
  try {
    await new Promise((resolve, reject) => {
      worker.stdout.on("data", chunk => { if (chunk.toString().includes("MODEL_REQUEST_STARTED")) resolve(); });
      worker.once("exit", code => reject(new Error(`Worker exited ${code}: ${errors}`)));
      worker.once("error", reject);
    });
    const exited = once(worker, "exit");
    worker.kill("SIGKILL");
    await exited;

    const command = (...parameters) => {
      const result = spawnSync(process.execPath, [...args, ...parameters], { env, encoding: "utf8", timeout: 15000 });
      assert.equal(result.status, 0, result.stderr || String(result.error));
      return result.stdout;
    };
    const before = JSON.parse(command("status", "offline-crash", "--json"));
    assert.equal(before.state, "pending");
    assert.ok(before.submission_id);

    const output = join(directory, "report.html");
    command("resume", "offline-crash", "--output", output);
    const after = JSON.parse(command("status", "offline-crash", "--json"));
    assert.equal(after.state, "complete");
    assert.equal(after.submission_id, before.submission_id);
    const html = await readFile(output, "utf8");
    assert.ok(html.includes("Budapest") && html.includes("Vienna"));
    assert.ok(html.includes('<span class="experiment">Pi</span>'));

    // A completed result exports again without another model request.
    const blocked = spawnSync(process.execPath, [...args, "resume", "offline-crash", "--output", output], {
      env: { ...env, PI_TEST_BLOCK: "1" }, encoding: "utf8", timeout: 10000,
    });
    assert.equal(blocked.status, 0, blocked.stderr);
    assert.ok(!blocked.stdout.includes("MODEL_REQUEST_STARTED"));
  } finally {
    if (worker.exitCode === null && worker.signalCode === null) worker.kill("SIGKILL");
    await rm(directory, { recursive: true, force: true });
  }
});
