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

for (const boundary of ["after-search", "during-search"]) {
  test(`Pi recovers ${boundary} with committed tool results in model context`, {
    timeout: 30000,
  }, async () => {
    const directory = await mkdtemp(join(tmpdir(), "pi-recovery-"));
    const env = {
      ...process.env,
      OPENAI_API_KEY: "fixture",
      OPENAI_MODEL: "gpt-6-luna",
      LOGFIRE_TOKEN: "",
      PI_TEST_BLOCK: "",
      PI_TEST_FAIL: "",
      PI_TEST_AUDIT: join(directory, "requests.jsonl"),
      PI_STATE_DIR: join(directory, "state"),
    };
    const worker = spawn(process.execPath, [...args, "run", "offline-crash"], {
      env: { ...env, PI_TEST_BLOCK: boundary },
      stdio: ["ignore", "pipe", "pipe"],
    });
    let errors = "";
    worker.stderr.on("data", (chunk) => {
      errors += chunk;
    });
    try {
      await new Promise((resolve, reject) => {
        worker.stdout.on("data", (chunk) => {
          if (chunk.toString().includes("CRASH_BOUNDARY_REACHED")) resolve();
        });
        worker.once("exit", (code) => reject(new Error(`Worker exited ${code}: ${errors}`)));
        worker.once("error", reject);
      });
      const exited = once(worker, "exit");
      worker.kill("SIGKILL");
      await exited;

      const command = (...parameters) => {
        const result = spawnSync(process.execPath, [...args, ...parameters], {
          env,
          encoding: "utf8",
          timeout: 15000,
        });
        assert.equal(result.status, 0, result.stderr || String(result.error));
        return result.stdout;
      };
      const before = JSON.parse(command("status", "offline-crash", "--json"));
      assert.equal(before.state, "pending");
      assert.ok(before.submission_id);

      const requests = async () =>
        (await readFile(env.PI_TEST_AUDIT, "utf8")).trim().split("\n").map(JSON.parse);
      const searchesBefore = (await requests()).filter((item) => item.search);
      assert.deepEqual(
        searchesBefore.map((item) => item.query),
        boundary === "after-search"
          ? ["current date and tomorrow date", "Budapest tomorrow"]
          : ["current date and tomorrow date", "Budapest tomorrow", "Vienna tomorrow"],
      );
      const savedTranscript = command("status", "offline-crash");
      assert.ok(
        savedTranscript.includes("toolResult") && savedTranscript.includes("Search answer"),
      );
      assert.ok(!savedTranscript.includes("history ends before this call completed"));
      const output = join(directory, "report.html");
      command("resume", "offline-crash", "--output", output);
      const after = JSON.parse(command("status", "offline-crash", "--json"));
      assert.equal(after.state, "complete");
      assert.equal(after.submission_id, before.submission_id);
      const html = await readFile(output, "utf8");
      assert.ok(html.includes("Budapest") && html.includes("Vienna"));
      assert.ok(html.includes('<span class="experiment">Pi</span>'));

      const searchesAfter = (await requests()).filter((item) => item.search);
      assert.equal(
        searchesAfter.filter((item) => item.query === "current date and tomorrow date").length,
        1,
      );
      assert.equal(searchesAfter.filter((item) => item.query === "Budapest tomorrow").length, 1);
      assert.equal(
        searchesAfter.filter((item) => item.query === "Vienna tomorrow").length,
        boundary === "during-search" ? 2 : 1,
      );
      const requestCount = (await requests()).length;

      // A completed result exports again without another model or tool request.
      const blocked = spawnSync(
        process.execPath,
        [...args, "resume", "offline-crash", "--output", output],
        {
          env: { ...env, PI_TEST_BLOCK: "all" },
          encoding: "utf8",
          timeout: 10000,
        },
      );
      assert.equal(blocked.status, 0, blocked.stderr);
      assert.ok(!blocked.stdout.includes("CRASH_BOUNDARY_REACHED"));
      assert.equal((await requests()).length, requestCount);
    } finally {
      if (worker.exitCode === null && worker.signalCode === null) worker.kill("SIGKILL");
      await rm(directory, { recursive: true, force: true });
    }
  });
}

test("Pi reports the native terminal provider error", async () => {
  const directory = await mkdtemp(join(tmpdir(), "pi-failure-"));
  const env = {
    ...process.env,
    OPENAI_API_KEY: "fixture",
    OPENAI_MODEL: "gpt-6-luna",
    LOGFIRE_TOKEN: "",
    PI_TEST_BLOCK: "",
    PI_TEST_FAIL: "1",
    PI_TEST_AUDIT: "",
    PI_STATE_DIR: directory,
  };
  try {
    const result = spawnSync(process.execPath, [...args, "run", "failed"], {
      env,
      encoding: "utf8",
      timeout: 15000,
    });
    assert.equal(result.status, 1);
    assert.ok(result.stderr.includes("Fixture provider quota exhausted"));
    const status = spawnSync(process.execPath, [...args, "status", "failed", "--json"], {
      env,
      encoding: "utf8",
      timeout: 15000,
    });
    assert.equal(status.status, 0, status.stderr);
    assert.equal(JSON.parse(status.stdout).state, "failed");
    assert.equal(JSON.parse(status.stdout).reason, "model_error");
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});
