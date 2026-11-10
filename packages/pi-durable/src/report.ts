import { randomUUID } from "node:crypto";
import { readFileSync } from "node:fs";
import { mkdir, rename, rm, writeFile } from "node:fs/promises";
import { dirname } from "node:path";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";

const fixtures = new URL("../../../core/src/weather_core/fixtures/", import.meta.url);
export const search = JSON.parse(readFileSync(new URL("search.json", fixtures), "utf8")) as {
  model: string; instructions: string;
};
const cities: string[][] = JSON.parse(readFileSync(new URL("cities.json", fixtures), "utf8"));
const ajv = new Ajv2020.default();
addFormats.default(ajv);
const valid = ajv.compile<BatchReport>(
  JSON.parse(readFileSync(new URL("report.schema.json", fixtures), "utf8")),
);

export interface BatchReport {
  forecast_date: string;
  summary: string;
  forecasts: {
    city: string;
    low_c: number;
    high_c: number;
    conditions: string;
    sources: { title: string; url: string }[];
  }[];
}

export interface BatchInput {
  forecast_date: string;
  city_batches: string[][];
  batch: number;
}

export function cityBatches(fixture: boolean): string[][] {
  return fixture ? cities[0].slice(0, 2).map(city => [city]) : cities;
}

export function validateBatch(result: unknown, input: BatchInput): BatchReport {
  if (!valid(result)) throw new Error("Invalid forecast response");
  const requested = input.city_batches[input.batch - 1];
  if (
    result.forecast_date !== input.forecast_date ||
    result.forecasts.length !== requested.length ||
    result.forecasts.some((row, index) => row.city !== requested[index] || row.low_c > row.high_c)
  ) {
    throw new Error("Forecast does not match the requested date or cities");
  }
  return result;
}

function escape(value: string): string {
  return value.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;").replaceAll("'", "&#39;");
}

export async function writeReport(path: string, results: BatchReport[]): Promise<void> {
  const date = escape(results[0].forecast_date);
  const summaries = results.map(batch => `<p>${escape(batch.summary)}</p>`).join("\n");
  const rows = results.flatMap(batch => batch.forecasts).map(row => {
    const sources = row.sources.map(src => `<a href="${escape(src.url)}">${escape(src.title)}</a>`).join(", ");
    return `<tr><th scope="row">${escape(row.city)}</th><td>${row.low_c}–${row.high_c} °C</td>`
      + `<td>${escape(row.conditions)}</td><td>${sources}</td></tr>`;
  }).join("");
  const html = '<!doctype html><html lang="en"><meta charset="utf-8">'
    + `<title>Weather forecast for ${date}</title><h1>Weather forecast for ${date}</h1>${summaries}`
    + '<table><thead><tr><th>City</th><th>Low–high</th><th>Conditions</th><th>Sources</th></tr>'
    + `</thead><tbody>${rows}</tbody></table></html>\n`;
  await mkdir(dirname(path), { recursive: true });
  const temporary = `${path}.${randomUUID()}.tmp`;
  try {
    await writeFile(temporary, html);
    await rename(temporary, path);
  } finally {
    await rm(temporary, { force: true });
  }
}
