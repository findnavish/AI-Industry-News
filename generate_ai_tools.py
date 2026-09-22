#!/usr/bin/env python3
"""
Daily job (NOT hourly): refreshes ai_tools_data.json used by generate_ai_news.py
to render the "AI Tools to Consider" section on ai_news.html.

Combines a manually-curated tool directory (ai_tools_curated.json) with a
best-effort supplemental list of recent tool-launch-flavored headlines pulled
via yfinance keyword search (there's no free structured "new AI tools" API,
so this is a heuristic supplement, not a guarantee of completeness).
Scheduled once/day via the com.essenn.ai-tools-daily launchd job.
"""
import json
import os
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CURATED_FILE = os.path.join(BASE_DIR, "ai_tools_curated.json")
OUTPUT_FILE = os.path.join(BASE_DIR, "ai_tools_data.json")
LOG_FILE = os.path.join(BASE_DIR, "dashboard.log")

TOOL_QUERIES = [
    "new AI tool launch",
    "AI app launch",
    "AI agent product release",
    "new AI feature announced",
]
MAX_PER_QUERY = 6
MAX_SUPPLEMENT = 12


def log(msg):
    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.now().isoformat()} ai_tools: {msg}\n")


def fetch_supplemental():
    import yfinance as yf
    seen = set()
    items = []
    for q in TOOL_QUERIES:
        try:
            s = yf.Search(q, news_count=MAX_PER_QUERY)
            news = s.news or []
        except Exception as e:
            log(f"tool search failed for '{q}': {e}")
            continue
        for n in news:
            link = n.get("link")
            title = n.get("title")
            if not title or not link or link in seen:
                continue
            seen.add(link)
            items.append({"title": title, "link": link, "publisher": n.get("publisher", "")})
    return items[:MAX_SUPPLEMENT]


def main():
    with open(CURATED_FILE) as f:
        curated = json.load(f)

    supplemental = fetch_supplemental()

    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_at_local": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
        "categories": curated["categories"],
        "comparisons": curated.get("comparisons", []),
        "supplemental_headlines": supplemental,
    }
    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=2)
    log(f"ai_tools_data refreshed OK, {len(supplemental)} supplemental headlines")
    print(f"AI tools data refreshed with {len(supplemental)} supplemental headlines")


if __name__ == "__main__":
    main()
