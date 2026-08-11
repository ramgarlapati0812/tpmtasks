#!/usr/bin/env python3
"""Generate a standalone HTML dashboard from dashboard.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = REPO_ROOT / "data" / "dashboard.json"
DEFAULT_OUTPUT = REPO_ROOT / "canvas" / "promo-cta-dashboard.html"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title}</title>
  <style>
    :root {{
      --bg: #0b1020;
      --panel: #121933;
      --panel-2: #1a2444;
      --text: #e5ecff;
      --muted: #93a4c7;
      --border: #2a3760;
      --accent: #6ea8fe;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, sans-serif;
      background: linear-gradient(180deg, #070b16 0%, var(--bg) 100%);
      color: var(--text);
      line-height: 1.5;
    }}
    .container {{ max-width: 1280px; margin: 0 auto; padding: 24px; }}
    header {{ margin-bottom: 24px; }}
    h1 {{ margin: 0 0 8px; font-size: 1.75rem; }}
    .subtitle {{ color: var(--muted); margin: 0; }}
    .meta {{ color: var(--muted); font-size: 0.875rem; margin-top: 8px; }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 12px;
      margin-bottom: 24px;
    }}
    .stat {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 14px 16px;
    }}
    .stat-label {{ color: var(--muted); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.04em; }}
    .stat-value {{ font-size: 1.5rem; font-weight: 700; margin-top: 4px; }}
    .tabs {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; }}
    .tab {{
      background: var(--panel);
      border: 1px solid var(--border);
      color: var(--text);
      padding: 8px 14px;
      border-radius: 999px;
      cursor: pointer;
    }}
    .tab.active {{ background: var(--accent); color: #081018; border-color: var(--accent); font-weight: 600; }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 16px;
      margin-bottom: 20px;
    }}
    .panel h2 {{ margin: 0 0 12px; font-size: 1.1rem; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.875rem; }}
    th, td {{ padding: 10px 8px; border-bottom: 1px solid var(--border); text-align: left; vertical-align: top; }}
    th {{ color: var(--muted); font-weight: 600; }}
    .badge {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: 999px;
      font-size: 0.75rem;
      font-weight: 600;
      background: var(--panel-2);
    }}
    .timeline {{ display: grid; gap: 10px; }}
    .milestone {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      padding: 10px 12px;
      background: var(--panel-2);
      border-radius: 10px;
    }}
    .hidden {{ display: none; }}
    .warnings {{
      background: #3b1f1f;
      border: 1px solid #7f1d1d;
      color: #fecaca;
      padding: 12px 14px;
      border-radius: 10px;
      margin-bottom: 16px;
      font-size: 0.875rem;
    }}
    .info {{
      background: #1e293b;
      border: 1px solid #334155;
      color: #cbd5e1;
      padding: 12px 14px;
      border-radius: 10px;
      margin-bottom: 16px;
      font-size: 0.875rem;
    }}
    .links {{ display: grid; gap: 8px; }}
    .links a {{
      color: var(--accent);
      text-decoration: none;
      padding: 10px 12px;
      background: var(--panel-2);
      border-radius: 8px;
      display: block;
    }}
    .links a:hover {{ text-decoration: underline; }}
    .ticket-link {{ color: var(--accent); text-decoration: none; }}
    .ticket-link:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>{title}</h1>
      <p class="subtitle">{subtitle}</p>
      <p class="meta">Last refreshed: {generated_at}</p>
    </header>

    {warnings_html}
    {info_html}

    <section>
      <h2>{summary_label}</h2>
      <div class="stats">{rollup_stats_html}</div>
    </section>

    {platform_section_html}

    <section class="panel">
      <h2>Milestone Timeline</h2>
      <div class="timeline">{milestones_html}</div>
    </section>

    <section class="panel">
      <h2>Risks and Blockers</h2>
      {blockers_table_html}
    </section>

    <section class="panel">
      <h2>Recent Activity</h2>
      {activity_table_html}
    </section>

    {resources_html}
  </div>

  {tabs_script}
</body>
</html>
"""


def badge(status: str, colors: dict[str, str]) -> str:
    color = colors.get(status, "#64748b")
    return f'<span class="badge" style="background:{color}; color:#081018">{status}</span>'


def stat_cards(stats: dict) -> str:
    labels = {
        "total_tasks": "Total Tasks",
        "complete": "Complete",
        "in_progress": "In Progress",
        "blocked": "Blocked",
        "percent_complete": "% Complete",
        "days_to_milestone": "Days to Milestone",
    }
    cards = []
    for key, label in labels.items():
        value = stats.get(key)
        if value is None:
            value = "—"
        elif key == "percent_complete":
            value = f"{value}%"
        cards.append(
            f'<div class="stat"><div class="stat-label">{label}</div>'
            f'<div class="stat-value">{value}</div></div>'
        )
    return "\n".join(cards)


def ticket_link(task_id: str) -> str:
    if "-" in task_id and task_id.split("-")[0].isalpha():
        url = f"https://wbdstreaming.atlassian.net/browse/{task_id}"
        return f'<a class="ticket-link" href="{url}" target="_blank" rel="noopener">{task_id}</a>'
    return task_id


def task_table(tasks: list[dict], extra_fields: list[str], colors: dict[str, str]) -> str:
    base_headers = ["ID", "Title", "Owner", "Status", "Priority", "Target Date", "Blocker", "Epic"]
    extra_headers = [field.replace("_", " ").title() for field in extra_fields]
    headers = base_headers + extra_headers

    rows = []
    for task in tasks:
        cells = [
            ticket_link(task.get("id", "")),
            task.get("title", ""),
            task.get("owner", ""),
            badge(task.get("status", ""), colors),
            task.get("priority", ""),
            task.get("target_date") or "—",
            "Yes" if task.get("blocker") else "No",
            task.get("epic") or "—",
        ]
        for field in extra_fields:
            cells.append(task.get(field) or "—")
        rows.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>")

    thead = "<tr>" + "".join(f"<th>{header}</th>" for header in headers) + "</tr>"
    tbody = "".join(rows) if rows else '<tr><td colspan="8">No tasks</td></tr>'
    return f"<table><thead>{thead}</thead><tbody>{tbody}</tbody></table>"


def render_dashboard(data: dict[str, object]) -> str:
    colors = data.get("status_colors", {})
    rollup_stats_html = stat_cards(data["rollup"])
    single_platform = data.get("single_platform", False)
    summary_label = data.get("summary_label", "Overall Summary")

    if single_platform:
        platform_id = next(iter(data["platforms"]))
        section = data["platforms"][platform_id]
        platform_section_html = (
            '<section class="panel">'
            f'<h2>{section["label"]} Tasks</h2>'
            f'{task_table(section["tasks"], section.get("extra_fields", []), colors)}'
            "</section>"
        )
        tabs_script = ""
    else:
        tabs = []
        panels = []
        for index, (platform_id, section) in enumerate(data["platforms"].items()):
            active = " active" if index == 0 else ""
            hidden = "" if index == 0 else " hidden"
            tabs.append(
                f'<button class="tab{active}" data-platform="{platform_id}">{section["label"]}</button>'
            )
            panels.append(
                f'<div id="panel-{platform_id}" class="platform-panel{hidden}">'
                f'<div class="stats">{stat_cards(section["stats"])}</div>'
                f'{task_table(section["tasks"], section.get("extra_fields", []), colors)}'
                f"</div>"
            )
        platform_section_html = (
            '<section class="panel">'
            "<h2>Platform Tasks</h2>"
            f'<div class="tabs">{"".join(tabs)}</div>'
            f'{"".join(panels)}'
            "</section>"
        )
        tabs_script = """
  <script>
    const tabs = document.querySelectorAll('.tab');
    const panels = document.querySelectorAll('.platform-panel');
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        tabs.forEach(t => t.classList.remove('active'));
        panels.forEach(p => p.classList.add('hidden'));
        tab.classList.add('active');
        document.getElementById('panel-' + tab.dataset.platform).classList.remove('hidden');
      });
    });
  </script>"""

    milestones = data.get("milestones", [])
    if milestones:
        milestones_html = "".join(
            f'<div class="milestone"><span>{item["name"]}</span>'
            f'<span>{item["date"]} · {item["platform"]}</span></div>'
            for item in milestones
        )
    else:
        milestones_html = "<p>No milestones configured.</p>"

    blockers = data.get("blockers", [])
    if blockers:
        blockers_table_html = (
            "<table><thead><tr>"
            "<th>Platform</th><th>ID</th><th>Title</th><th>Owner</th>"
            "<th>Status</th><th>Reason</th><th>Target Date</th>"
            "</tr></thead><tbody>"
            + "".join(
                "<tr>"
                f"<td>{item['platform']}</td>"
                f"<td>{ticket_link(item['id'])}</td>"
                f"<td>{item['title']}</td>"
                f"<td>{item['owner']}</td>"
                f"<td>{badge(item['status'], colors)}</td>"
                f"<td>{item.get('blocker_reason') or '—'}</td>"
                f"<td>{item.get('target_date') or '—'}</td>"
                "</tr>"
                for item in blockers
            )
            + "</tbody></table>"
        )
    else:
        blockers_table_html = "<p>No blockers 🎉</p>"

    activity = data.get("recent_activity", [])
    if activity:
        activity_table_html = (
            "<table><thead><tr><th>Date</th><th>ID</th><th>Title</th><th>Change</th><th>Platform</th></tr></thead><tbody>"
            + "".join(
                "<tr>"
                f"<td>{item['date']}</td>"
                f"<td>{ticket_link(item['id'])}</td>"
                f"<td>{item['title']}</td>"
                f"<td>{item['change']}</td>"
                f"<td>{item['platform']}</td>"
                "</tr>"
                for item in activity
            )
            + "</tbody></table>"
        )
    else:
        activity_table_html = "<p>No recent activity in the last 7 days.</p>"

    warnings = data.get("warnings", [])
    warnings_html = ""
    if warnings:
        items = "".join(f"<li>{warning}</li>" for warning in warnings[:5])
        warnings_html = f'<div class="warnings"><strong>Data warnings</strong><ul>{items}</ul></div>'

    info_html = ""
    if data.get("data_note"):
        info_html = f'<div class="info">{data["data_note"]}</div>'

    resources = data.get("resources", [])
    if resources:
        links = "".join(
            f'<a href="{item["url"]}" target="_blank" rel="noopener">{item["label"]}</a>'
            for item in resources
        )
        resources_html = f'<section class="panel"><h2>Project Resources</h2><div class="links">{links}</div></section>'
    else:
        resources_html = ""

    return HTML_TEMPLATE.format(
        title=data.get("title", "Dashboard"),
        subtitle=data.get("subtitle", ""),
        generated_at=data.get("generated_at", ""),
        warnings_html=warnings_html,
        info_html=info_html,
        summary_label=summary_label,
        rollup_stats_html=rollup_stats_html,
        platform_section_html=platform_section_html,
        milestones_html=milestones_html,
        blockers_table_html=blockers_table_html,
        activity_table_html=activity_table_html,
        resources_html=resources_html,
        tabs_script=tabs_script,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    with args.input.open(encoding="utf-8") as handle:
        data = json.load(handle)

    html = render_dashboard(data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html, encoding="utf-8")
    print(f"Wrote dashboard HTML to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
