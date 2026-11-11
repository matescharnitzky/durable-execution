import assert from "node:assert/strict";
import { appendFileSync, readFileSync } from "node:fs";
import { mock } from "node:test";
import { createAssistantMessageEventStream } from "@earendil-works/pi-ai/utils/event-stream";

const fixture = readFileSync(new URL("../../../core/tests/report.json", import.meta.url), "utf8");
const queries = ["current date and tomorrow date", "Budapest tomorrow", "Vienna tomorrow"];
const source = { type: "url_citation", title: "Forecast", url: "https://weather.example.org/forecast" };
const usage = { input: 1, output: 1, cacheRead: 0, cacheWrite: 0, totalTokens: 2,
  cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 } };

mock.module("@earendil-works/pi-ai/api/openai-responses", {
  exports: {
    streamSimple(model, transcript, options) {
      const input = { messages: transcript.messages };
      const functions = [{ type: "function", name: "web_search" }];
      const payload = options.onPayload({ input, tools: functions }, model);
      assert.equal(payload.input, input);
      const search = payload.tools[0].type === "web_search";
      const results = transcript.messages.filter(message => message.role === "toolResult");
      const query = search ? transcript.messages.find(message => message.role === "user").content : undefined;
      if (process.env.PI_TEST_AUDIT) appendFileSync(process.env.PI_TEST_AUDIT, JSON.stringify({ search, query, results: results.length }) + "\n");
      if (search) {
        assert.equal(payload.tool_choice, "required");
        assert.equal(payload.text, undefined);
      } else {
        assert.equal(payload.tools, functions); // Function tools must survive the payload hook.
        assert.equal(payload.parallel_tool_calls, false);
        assert.equal(payload.text.format.strict, true);
        const urlSchema = payload.text.format.schema.properties.forecasts.items.properties.sources.items.properties.url;
        assert.equal(urlSchema.format, undefined);
        assert.equal(urlSchema.pattern, "^https?://");
        const instructions = transcript.messages.filter(message => message.role === "system").map(message => [
          typeof message.content === "string" ? message.content : message.content.map(part => part.text).join(" "),
          ...Object.values(message.sections || {}),
        ].join(" ")).join(" ");
        assert.ok(instructions.includes("tomorrow") && instructions.includes("Budapest"));
        for (const result of results) {
          assert.equal(result.isError, false);
          const saved = JSON.parse(result.content.find(part => part.type === "text").text);
          assert.equal(saved.sources[0].url, source.url);
          assert.ok(saved.answer.includes("Search answer"));
        }
      }
      const stream = createAssistantMessageEventStream();
      if (process.env.PI_TEST_BLOCK === "all" ||
          (process.env.PI_TEST_BLOCK === "after-search" && !search && results.length === 2) ||
          (process.env.PI_TEST_BLOCK === "during-search" && search && query === queries[2])) {
        process.stdout.write("CRASH_BOUNDARY_REACHED\n");
        return stream;
      }
      queueMicrotask(async () => {
        if (search) await options.onProviderStreamEvent({ type: "response.output_text.annotation.added", annotation: source }, model);
        const failure = process.env.PI_TEST_FAIL === "1";
        const toolCall = !search && !failure && results.length < queries.length;
        const message = {
          role: "assistant", api: model.api, provider: model.provider, model: model.id,
          content: failure ? [] : toolCall ? [{ type: "toolCall", id: `call_${results.length}`, name: "web_search", arguments: { query: queries[results.length] } }]
            : [{ type: "text", text: search ? `Search answer for ${query}` : fixture }],
          errorMessage: failure ? "Fixture provider quota exhausted" : undefined,
          stopReason: failure ? "error" : toolCall ? "toolUse" : "stop", timestamp: Date.now(), usage,
        };
        stream.push({ type: "start", partial: message });
        stream.push(message.stopReason === "error" ? { type: "error", reason: "error", error: message }
          : { type: "done", reason: message.stopReason, message });
      });
      return stream;
    },
  },
});
