import type { Model, ProviderStreams } from "@earendil-works/pi-ai";
import { streamSimple } from "@earendil-works/pi-ai/api/openai-responses";
import { createModels, createProvider } from "@earendil-works/pi-ai/models";
import { openaiProvider } from "@earendil-works/pi-ai/providers/openai";

import { reportSchema, settings } from "./config.ts";

export const modelRef = { provider: "openai", modelId: settings.openaiModel };

// OpenAI strict output accepts a subset of JSON Schema; core still validates URI format.
const outputSchema = structuredClone(reportSchema);
delete (
  outputSchema.properties.forecasts.items.properties.sources.items.properties.url as {
    format?: string;
  }
).format;

const streamWeather: ProviderStreams["streamSimple"] = (model, transcript, options) =>
  streamSimple(model as Model<"openai-responses">, transcript, {
    ...options,
    onPayload(payload) {
      return {
        ...(payload as Record<string, unknown>),
        parallel_tool_calls: false,
        text: {
          format: {
            type: "json_schema",
            name: "weather_report",
            strict: true,
            schema: outputSchema,
          },
        },
      };
    },
  });

export function openaiModels(stream: ProviderStreams["streamSimple"] = streamWeather) {
  const openai = openaiProvider();
  const model = openai.getModels().find((model) => model.id === settings.openaiModel);
  if (!model) throw new Error(`Pi's OpenAI catalog has no model ${settings.openaiModel}`);
  const models = createModels();
  models.setProvider(
    createProvider({
      id: "openai",
      auth: openai.auth,
      models: [{ ...model, baseUrl: settings.openaiBaseUrl || model.baseUrl }],
      api: { stream, streamSimple: stream },
    }),
  );
  return models;
}
