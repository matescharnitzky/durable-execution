import { readFileSync } from "node:fs";

const core = new URL("../../core/src/weather_core/", import.meta.url);

export const settings = {
  openaiModel: process.env.OPENAI_MODEL || "gpt-6-luna",
  openaiBaseUrl: process.env.OPENAI_BASE_URL,
  stateDirectory: process.env.PI_STATE_DIR || "artifacts/pi/state",
};

const prompts = JSON.parse(readFileSync(new URL("prompt.json", core), "utf8"));
export const systemPrompt: string = prompts.system_prompt;
export const webSearchInstructions: string = prompts.web_search_instructions;
export const reportSchema = JSON.parse(readFileSync(new URL("report_schema.json", core), "utf8"));
