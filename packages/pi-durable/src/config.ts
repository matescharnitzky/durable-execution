import { readFileSync } from "node:fs";

const core = new URL("../../../core/src/weather_core/", import.meta.url);

export const settings = {
  openaiModel: process.env.OPENAI_MODEL || "gpt-5.4-mini",
  openaiBaseUrl: process.env.OPENAI_BASE_URL,
  stateDirectory: process.env.PI_STATE_DIR || "artifacts/pi/state",
};

export const systemPrompt: string = JSON.parse(readFileSync(new URL("prompt.json", core), "utf8")).system_prompt;
export const reportSchema = JSON.parse(readFileSync(new URL("report_schema.json", core), "utf8"));
