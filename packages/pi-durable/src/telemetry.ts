import { ROOT_CONTEXT, SpanStatusCode, trace, type Attributes, type Context } from "@opentelemetry/api";
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-http";
import { NodeTracerProvider, SimpleSpanProcessor } from "@opentelemetry/sdk-trace-node";
import type { TelemetryContext, TelemetrySpan } from "@earendil-works/pi-telemetry";

export function logfireTelemetry(runId: string) {
  const token = process.env.LOGFIRE_TOKEN;
  if (!token) return undefined;
  const region = /^pylf_v\d+_eu_/.test(token) ? "eu" : "us";
  const baseUrl = process.env.LOGFIRE_BASE_URL || `https://logfire-${region}.pydantic.dev`;
  const exporter = new OTLPTraceExporter({
    url: process.env.LOGFIRE_OTLP_TRACES_URL || `${baseUrl.replace(/\/$/, "")}/v1/traces`,
    headers: { Authorization: token },
  });
  const provider = new NodeTracerProvider({ spanProcessors: [new SimpleSpanProcessor(exporter)] });
  const tracer = provider.getTracer("pi-durable-report");
  const contexts = new WeakMap<TelemetryContext, Context>();

  function adapter(parent: Context): TelemetryContext {
    return {
      async startSpan(options, callback) {
        const span = tracer.startSpan(options.name, {
          attributes: {
            ...options.attributes as Attributes,
            "durable.runtime": "pi",
            "durable.run_id": runId,
          },
        }, parent);
        const current = trace.setSpan(parent, span);
        const child: TelemetrySpan = {
          ...adapter(current),
          addEvent: (name, attributes) => { span.addEvent(name, attributes as Attributes); },
          addLink: link => {
            const context = contexts.get(link.context);
            const linked = context && trace.getSpanContext(context);
            if (linked) span.addLink({ context: linked, attributes: link.attributes as Attributes });
          },
          setAttributes: attributes => { span.setAttributes(attributes as Attributes); },
          setStatus: status => {
            span.setStatus({ code: status.status === "ok" ? SpanStatusCode.OK : SpanStatusCode.ERROR });
          },
        };
        contexts.set(child, current);
        for (const link of options.links ?? []) child.addLink(link);
        try {
          return await callback(child);
        } catch (error) {
          span.setStatus({ code: SpanStatusCode.ERROR });
          throw error;
        } finally {
          span.end();
        }
      },
    };
  }
  return { context: adapter(ROOT_CONTEXT), close: () => provider.shutdown() };
}
