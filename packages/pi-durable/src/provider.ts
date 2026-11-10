import { createModels, createProvider } from "@earendil-works/pi-ai/models";
import { openaiProvider } from "@earendil-works/pi-ai/providers/openai";
import type { AssistantMessage, Model, SimpleStreamOptions, TranscriptContext } from "@earendil-works/pi-ai";
import { createAssistantMessageEventStream } from "@earendil-works/pi-ai/utils/event-stream";

import { search, validateBatch, type BatchInput } from "./report.ts";

const model: Model<"openai-responses"> = {
  id: "openai-responses-web-search",
  name: "OpenAI Responses web search",
  provider: "weather-search",
  api: "openai-responses",
  baseUrl: (process.env.OPENAI_BASE_URL || "https://api.openai.com/v1").replace(/\/$/, ""),
  reasoning: false,
  input: ["text"],
  contextWindow: 128_000,
  maxTokens: 8_000,
  cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
};

export const modelRef = { provider: model.provider, modelId: model.id };

interface ResponsesOutput {
  id?: string;
  model?: string;
  usage?: { input_tokens: number; output_tokens: number; total_tokens: number };
  output: { type: string; content?: { type: string; text?: string }[] }[];
}

async function forecast(input: BatchInput, signal?: AbortSignal): Promise<ResponsesOutput> {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) throw new Error("OPENAI_API_KEY is required");
  const request = {
    model: process.env.OPENAI_MODEL || search.model,
    tools: [{ type: "web_search" }],
    tool_choice: "required",
    instructions: search.instructions,
    input: JSON.stringify({
      forecast_date: input.forecast_date,
      cities: input.city_batches[input.batch - 1],
    }),
  };
  const timeout = AbortSignal.timeout(90_000);
  const response = await fetch(`${model.baseUrl}/responses`, {
    method: "POST",
    headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
    body: JSON.stringify(request),
    signal: signal ? AbortSignal.any([signal, timeout]) : timeout,
  });
  if (!response.ok) {
    await response.body?.cancel();
    throw new Error(`OpenAI HTTP ${response.status}`);
  }
  return response.json() as Promise<ResponsesOutput>;
}

function stream(_model: Model<string>, transcript: TranscriptContext, options?: SimpleStreamOptions) {
  const events = createAssistantMessageEventStream();
  const initial: AssistantMessage = {
    role: "assistant", content: [], api: model.api, provider: model.provider, model: model.id,
    usage: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, totalTokens: 0, cost: { ...model.cost, total: 0 } },
    stopReason: "pending", timestamp: Date.now(),
  };
  events.push({ type: "start", partial: initial });
  void (async () => {
    try {
      const prompt = transcript.messages.findLast(message => message.role === "user");
      if (typeof prompt?.content !== "string") throw new Error("Missing forecast input");
      const input: BatchInput = JSON.parse(prompt.content);
      const response = await forecast(input, options?.signal);
      const raw = response.output.filter(item => item.type === "message")
        .flatMap(item => item.content ?? []).filter(part => part.type === "output_text")
        .map(part => part.text).join("").trim().replace(/^```json\s*|\s*```$/g, "");
      const result = validateBatch(JSON.parse(raw), input);
      const message: AssistantMessage = {
        ...initial,
        responseId: response.id,
        responseModel: response.model,
        stopReason: "stop",
        usage: {
          ...initial.usage,
          input: response.usage?.input_tokens ?? 0,
          output: response.usage?.output_tokens ?? 0,
          totalTokens: response.usage?.total_tokens ?? 0,
        },
        content: [{ type: "text", text: JSON.stringify(result) }],
      };
      events.push({ type: "done", reason: "stop", message });
    } catch (error) {
      const reason = options?.signal?.aborted ? "aborted" : "error";
      const errorMessage = error instanceof SyntaxError ? "Invalid forecast JSON"
        : error instanceof Error ? error.message : "Forecast request failed";
      events.push({ type: "error", reason, error: { ...initial, stopReason: reason, errorMessage } });
    }
  })();
  return events;
}

export function forecastModels() {
  const models = createModels();
  models.setProvider(createProvider({
    id: model.provider,
    auth: openaiProvider().auth,
    models: [model],
    api: { stream, streamSimple: stream },
  }));
  return models;
}
