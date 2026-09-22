#!/usr/bin/env python3
"""
Generates ai_news.html: broader AI-industry developments (not limited to
tickers you hold) via yfinance's keyword news search, deduplicated and
sorted by recency. Run alongside the other dashboard generators hourly.
"""
import json
import os
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(BASE_DIR, "index.html")
LOG_FILE = os.path.join(BASE_DIR, "dashboard.log")

QUERIES = [
    "artificial intelligence",
    "AI chips",
    "OpenAI",
    "Nvidia AI",
    "Microsoft AI",
    "AI startup funding",
    "AI regulation",
    "generative AI",
]
MAX_PER_QUERY = 8
MAX_TOTAL = 40


def log(msg):
    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.now().isoformat()} ai_news: {msg}\n")


def time_ago(ts):
    try:
        pub = datetime.fromtimestamp(ts, tz=timezone.utc)
        delta = datetime.now(timezone.utc) - pub
        hours = delta.total_seconds() / 3600
        if hours < 1:
            return f"{int(delta.total_seconds()/60)}m ago", pub
        if hours < 24:
            return f"{int(hours)}h ago", pub
        return f"{int(hours/24)}d ago", pub
    except Exception:
        return "", None


def fetch_all():
    import yfinance as yf
    seen_links = set()
    items = []
    for q in QUERIES:
        try:
            s = yf.Search(q, news_count=MAX_PER_QUERY)
            news = s.news or []
        except Exception as e:
            log(f"search failed for '{q}': {e}")
            continue
        for n in news:
            link = n.get("link")
            title = n.get("title")
            if not title or not link or link in seen_links:
                continue
            seen_links.add(link)
            ago, pub_dt = time_ago(n.get("providerPublishTime"))
            related = ", ".join(n.get("relatedTickers", []) or [])
            items.append({
                "title": title,
                "link": link,
                "publisher": n.get("publisher", ""),
                "ago": ago,
                "pub_dt": pub_dt,
                "related": related,
                "query": q,
            })
    # sort newest first; items without a timestamp go last
    items.sort(key=lambda x: x["pub_dt"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return items[:MAX_TOTAL]


def load_tools_section():
    tools_file = os.path.join(BASE_DIR, "ai_tools_data.json")
    if not os.path.exists(tools_file):
        return "", "", ""
    with open(tools_file) as f:
        data = json.load(f)
    refreshed = data.get("generated_at_local", "unknown")

    cat_html = ""
    for cat in data.get("categories", []):
        tool_items = ""
        for t in cat.get("tools", []):
            tool_items += f"""
            <li><a href="{t['link']}" target="_blank" rel="noopener">{t['name']}</a><div class="desc">{t['desc']}</div></li>"""
        cat_html += f"""
        <div class="tool-card">
          <h3>{cat['category']}</h3>
          <ul class="tool-list">{tool_items}</ul>
        </div>"""

    supp = data.get("supplemental_headlines", [])
    supp_html = ""
    if supp:
        supp_items = "".join(
            f'<li><a href="{s["link"]}" target="_blank" rel="noopener">{s["title"]}</a> <span class="pub">— {s.get("publisher","")}</span></li>'
            for s in supp
        )
        supp_html = f"""
        <div class="tool-card" style="grid-column:1/-1;">
          <h3>Recent Tool-Launch Headlines (best-effort)</h3>
          <ul class="tool-list">{supp_items}</ul>
        </div>"""

    section = f"""
  <h2>🛠️ New AI Tools to Consider <span class="refresh-badge">refreshed daily · last: {refreshed}</span></h2>
  <div class="tool-grid">
    {cat_html}
    {supp_html}
  </div>"""

    # Side-by-side feature comparison tables, one per domain
    compare_html = ""
    for comp in data.get("comparisons", []):
        features = comp["features"]
        header_cells = "".join(f"<th>{feat}</th>" for feat in features)
        body_rows = ""
        for t in comp["tools"]:
            value_cells = "".join(f"<td>{v}</td>" for v in t["values"])
            body_rows += f"<tr><td class=\"tool-name\">{t['name']}</td>{value_cells}</tr>"
        compare_html += f"""
        <div class="compare-block">
          <h3>{comp['domain']}</h3>
          <div class="table-scroll">
            <table class="compare-table">
              <thead><tr><th>Tool</th>{header_cells}</tr></thead>
              <tbody>{body_rows}</tbody>
            </table>
          </div>
        </div>"""

    comparison_section = f"""
  <h2>📊 Side-by-Side Feature Comparison <span class="refresh-badge">refreshed daily · last: {refreshed}</span></h2>
  {compare_html}""" if compare_html else ""

    return section, comparison_section, refreshed


def main():
    items = fetch_all()
    now = datetime.now().strftime("%Y-%m-%d %I:%M %p")
    tools_section, comparison_section, tools_refreshed = load_tools_section()

    rows_html = ""
    for it in items:
        related_html = f'<span class="tag">{it["related"]}</span>' if it["related"] else ""
        rows_html += f"""
        <li>
          <div class="headline"><a href="{it['link']}" target="_blank" rel="noopener">{it['title']}</a></div>
          <div class="meta">{it['publisher']}{' · ' + it['ago'] if it['ago'] else ''} · <span class="query">via "{it['query']}"</span> {related_html}</div>
        </li>"""

    if not items:
        rows_html = '<li class="none">No AI news retrieved this cycle — will retry next hour.</li>'

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>AI Industry Developments</title>
<style>
  body {{ font-family: -apple-system, Helvetica, Arial, sans-serif; background:#0d1117; color:#e6edf3; margin:0; padding:24px; }}
  h1 {{ font-size: 22px; margin-bottom:4px; }}
  .nav a {{ color:#58a6ff; text-decoration:none; margin-right:16px; font-size:13px; }}
  .updated {{ color:#8b949e; font-size:13px; margin:10px 0 20px; }}
  ul {{ list-style:none; margin:0; padding:0; max-width:900px; }}
  li {{ background:#161b22; border:1px solid #30363d; border-radius:8px; padding:14px 18px; margin-bottom:12px; }}
  li.none {{ color:#8b949e; background:none; border:none; }}
  .headline a {{ color:#e6edf3; text-decoration:none; font-size:14.5px; font-weight:600; }}
  .headline a:hover {{ color:#58a6ff; text-decoration:underline; }}
  .meta {{ color:#8b949e; font-size:12px; margin-top:6px; }}
  .query {{ color:#6e7681; font-style:italic; }}
  .tag {{ background:#1f6feb22; color:#58a6ff; border:1px solid #1f6feb55; border-radius:10px; padding:1px 8px; margin-left:6px; font-size:11px; }}
  .refresh-badge {{ color:#8b949e; font-size:11px; font-weight:400; margin-left:8px; }}
  .tool-grid {{ display:grid; grid-template-columns: repeat(auto-fill, minmax(280px,1fr)); gap:14px; margin:14px 0 30px; max-width:1200px; }}
  .tool-card {{ background:#161b22; border:1px solid #30363d; border-radius:8px; padding:14px 18px; }}
  .tool-card h3 {{ margin:0 0 8px 0; font-size:14px; color:#e6edf3; }}
  .tool-list {{ list-style:none; margin:0; padding:0; }}
  .tool-list li {{ margin-bottom:10px; padding:0; background:none; border:none; }}
  .tool-list a {{ color:#58a6ff; text-decoration:none; font-weight:600; font-size:13px; }}
  .tool-list a:hover {{ text-decoration:underline; }}
  .tool-list .desc {{ color:#8b949e; font-size:12px; margin-top:2px; }}
  .tool-list .pub {{ color:#6e7681; font-size:11px; }}
  .compare-block {{ margin-bottom:26px; max-width:1200px; }}
  .compare-block h3 {{ font-size:14px; margin:0 0 8px 0; }}
  .table-scroll {{ overflow-x:auto; border:1px solid #30363d; border-radius:8px; }}
  table.compare-table {{ width:100%; border-collapse:collapse; font-size:12.5px; min-width:640px; }}
  table.compare-table th {{ text-align:left; color:#8b949e; font-weight:600; padding:8px 12px; border-bottom:1px solid #30363d; background:#161b22; white-space:nowrap; }}
  table.compare-table td {{ padding:8px 12px; border-bottom:1px solid #21262d; background:#0d1117; vertical-align:top; }}
  table.compare-table td.tool-name {{ font-weight:600; color:#58a6ff; white-space:nowrap; }}
  table.compare-table tr:last-child td {{ border-bottom:none; }}
</style>
</head>
<body>
  <h1>🤖 AI Industry — Latest Developments</h1>
    <div class="updated">Last updated: {now} (UTC via GitHub Actions) &nbsp;|&nbsp; Auto-refreshes daily &nbsp;|&nbsp; Aggregated across {len(QUERIES)} topic searches (Yahoo Finance)</div>
  {tools_section}
  {comparison_section}
  <h2>📰 Latest Headlines</h2>
  <ul>
    {rows_html}
  </ul>
</body>
</html>"""

    with open(OUTPUT_FILE, "w") as f:
        f.write(html)
    log(f"ai_news page generated OK with {len(items)} items")
    print(f"AI news page written to {OUTPUT_FILE} with {len(items)} items")


if __name__ == "__main__":
    main()
