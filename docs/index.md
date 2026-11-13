# Durable execution lab

This lab compares how four implementations recover interrupted weather-report runs:
LangGraph, Pydantic AI with DBOS, Pydantic AI with Temporal, and Pi Durable.

Each uses the same prompt, report schema, and HTML renderer. The agent checks tomorrow’s date,
researches five cities through sequential searches, and produces a report with source URLs.
The default model is `gpt-6-luna`; `OPENAI_MODEL` overrides it.

Start with [installation](getting-started.md), explore the [architecture](architecture.md),
then follow [recovery and validation](recovery.md) and the runtime guides.

Durability means reusing persisted work after interruption. It does not guarantee that an
external API call happens exactly once, or that a generated forecast is accurate.
