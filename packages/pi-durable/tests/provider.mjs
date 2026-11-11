import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { mock } from "node:test";
import { createAssistantMessageEventStream } from "@earendil-works/pi-ai/utils/event-stream";

const fixture = readFileSync(new URL("../../../core/tests/report.json", import.meta.url), "utf8");

mock.module("@earendil-works/pi-ai/api/openai-responses", {
  namedExports: {
    streamSimple(model, transcript, options) {
      const input = { messages: transcript.messages };
      const payload = options.onPayload({ input }, model);
      assert.equal(payload.input, input);
      assert.equal(payload.tools[0].type, "web_search");
      assert.equal(payload.text.format.type, "json_schema");
      assert.equal(payload.text.format.strict, true);
      assert.ok(transcript.messages.some(message => message.role === "user"));
      assert.ok(transcript.messages.some(message => message.role === "system"
        && typeof message.content === "string" && message.content.includes("tomorrow")
        && message.content.includes("Budapest")));
      const stream = createAssistantMessageEventStream();
      if (process.env.PI_TEST_BLOCK === "1") {
        process.stdout.write("MODEL_REQUEST_STARTED\n");
        return stream;
      }
      queueMicrotask(() => {
        stream.push({ type: "done", reason: "stop", message: {
          role: "assistant", api: model.api, provider: model.provider, model: model.id,
          content: [{ type: "text", text: fixture }], stopReason: "stop", timestamp: Date.now(),
          usage: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, totalTokens: 0,
            cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 } },
        } });
      });
      return stream;
    },
  },
});
