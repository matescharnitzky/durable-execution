import { streamSimple } from "@earendil-works/pi-ai/api/openai-responses";
import { defineTool } from "@earendil-works/pi-durable";
import { obj, str } from "@earendil-works/pi-schema";

import { webSearchInstructions } from "./config.ts";
import { openaiModels, modelRef } from "./provider.ts";

export const webSearch = defineTool({
  name: "web_search",
  description: "Search the web for current information and source URLs for the query.",
  parameters: obj({ query: str() }),
  // Searching is read-only: Pi may restart a search whose result was not committed.
  replay: "safe",
  async execute({ query }, _api, context) {
    const models = openaiModels(streamSimple);
    const model = models.getModel(modelRef.provider, modelRef.modelId)!;
    const sources = new Map<string, { title: string; url: string }>();
    const response = await models.completeSimple(model, {
      systemPrompt: webSearchInstructions,
      messages: [{ role: "user", content: query, timestamp: Date.now() }],
    }, {
      signal: context.abortSignal,
      onPayload(payload) {
        return { ...(payload as Record<string, unknown>), tools: [{ type: "web_search" }], tool_choice: "required" };
      },
      onProviderStreamEvent(event) {
        // Pi's text blocks omit Responses URL annotations; preserve the native citations.
        const item = event as { type: string; annotation?: { type: string; title: string; url: string } };
        if (item.type === "response.output_text.annotation.added" && item.annotation?.type === "url_citation") {
          const { title, url } = item.annotation;
          sources.set(url, { title, url });
        }
      },
    });
    if (response.stopReason === "error" || response.stopReason === "aborted") {
      throw new Error(response.errorMessage || "Web search failed");
    }
    const answer = response.content.filter(part => part.type === "text").map(part => part.text).join("");
    return {
      output: [{ type: "text", text: JSON.stringify({ answer, sources: [...sources.values()] }) }],
      usage: response.usage,
    };
  },
});
