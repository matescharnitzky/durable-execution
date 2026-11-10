import { streamSimple } from "@earendil-works/pi-ai/api/openai-responses";
import { createModels, createProvider } from "@earendil-works/pi-ai/models";
import { openaiProvider } from "@earendil-works/pi-ai/providers/openai";
import type { Model, ProviderStreams } from "@earendil-works/pi-ai";

import { search, type BatchInput } from "./report.ts";

export const modelRef = { provider: "weather-search", modelId: "openai-responses-web-search" };

const streamWeather: ProviderStreams["streamSimple"] = (model, transcript, options) =>
  streamSimple(model as Model<"openai-responses">, transcript, {
    ...options,
    maxRetries: 0,
    timeoutMs: 90_000,
    onPayload(payload) {
      const prompt = transcript.messages.findLast(message => message.role === "user");
      if (typeof prompt?.content !== "string") throw new Error("Missing forecast input");
      const input: BatchInput = JSON.parse(prompt.content);
      return {
        ...(payload as Record<string, unknown>),
        model: process.env.OPENAI_MODEL || search.model,
        tools: [{ type: "web_search" }],
        tool_choice: "required",
        instructions: search.instructions,
        input: JSON.stringify({
          forecast_date: input.forecast_date,
          cities: input.city_batches[input.batch - 1],
        }),
      };
    },
  });

export function forecastModels() {
  const openai = openaiProvider();
  const model = openai.getModels().find(model => model.id === search.model);
  if (!model) throw new Error(`Pi's OpenAI catalog has no model ${search.model}`);
  const models = createModels();
  models.setProvider(createProvider({
    id: modelRef.provider,
    auth: openai.auth,
    models: [{
      ...model,
      id: modelRef.modelId,
      provider: modelRef.provider,
      baseUrl: process.env.OPENAI_BASE_URL || model.baseUrl,
    }],
    api: { stream: streamWeather, streamSimple: streamWeather },
  }));
  return models;
}
