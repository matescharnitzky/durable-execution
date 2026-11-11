REPORT_PROMPT = (
    "Call web_search to collect forecasts and source URLs before writing the report. "
    "Use web search to find forecasts for the requested local calendar date and cities. "
    "Return only a JSON object with forecast_date, summary, and forecasts. "
    "Each forecast must include city, low_c, high_c, conditions, and sources "
    "(objects with title and URL in the url field). Use exact input city names "
    "in order, Celsius, and real forecast sources. Never invent data."
)
