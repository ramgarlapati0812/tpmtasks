#!/usr/bin/env python3
"""Fetch TPM task data for the multi-platform dashboard.

Supports CSV (default MVP) and optional Jira API imports.
Outputs normalized JSON grouped by platform.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO_ROOT / "config"
DEFAULT_TASKS_CSV = REPO_ROOT / "data" / "sample_tasks.csv"
DEFAULT_MILESTONES_CSV = REPO_ROOT / "data" / "milestones.csv"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "dashboard.json"
DEFAULT_ENV_FILE = REPO_ROOT / ".env"


def load_env_file(path: Path = DEFAULT_ENV_FILE) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


def load_yaml(path: Path) -> dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML is required. Install with: pip install pyyaml")
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def normalize_header(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def resolve_csv_column(row: dict[str, str], field: str, aliases: dict[str, list[str]]) -> str:
    alias_list = aliases.get(field, [field])
    normalized_row = {normalize_header(k): v for k, v in row.items()}
    for alias in alias_list:
        key = normalize_header(alias)
        if key in normalized_row:
            value = normalized_row[key]
            if value is not None and str(value).strip():
                return str(value).strip()
    return ""


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"yes", "true", "1", "y", "blocked"}


def parse_date(value: str) -> str | None:
    if not value or not value.strip():
        return None
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return value


def match_platform(raw_platform: str, platforms: list[dict[str, Any]]) -> str | None:
    token = raw_platform.strip().lower()
    if not token:
        return None
    for platform in platforms:
        if token == platform["id"]:
            return platform["id"]
        for candidate in platform.get("csv_values", []):
            if token == candidate.lower():
                return platform["id"]
        for component in platform.get("jira_components", []):
            if token == component.lower():
                return platform["id"]
        for group in platform.get("jira_groups", []):
            if token == group.lower():
                return platform["id"]
    return None


def resolve_jira_platform(
    issue: dict[str, Any],
    fields: dict[str, Any],
    platforms: list[dict[str, Any]],
    platform_field: str,
) -> str | None:
    for component in fields.get("components", []):
        platform_id = match_platform(component.get("name", ""), platforms)
        if platform_id:
            return platform_id

    group_values = fields.get(platform_field) or []
    if not isinstance(group_values, list):
        group_values = [group_values]
    for option in group_values:
        value = option.get("value", "") if isinstance(option, dict) else str(option)
        platform_id = match_platform(value, platforms)
        if platform_id:
            return platform_id

    summary = fields.get("summary", "")
    title_patterns = {
        "apple": ["[gcx apple]", "gcx apple"],
        "android": ["[gcx android]", "gcx android"],
        "lightbeam": ["[gcx lb]", "[gcx lightbeam]", "gcx lightbeam", "gcx lb"],
        "roku": ["[gcx roku]", "gcx roku"],
    }
    summary_lower = summary.lower()
    for platform_id, patterns in title_patterns.items():
        if any(pattern in summary_lower for pattern in patterns):
            return platform_id

    return None


def compute_stats(tasks: list[dict[str, Any]], milestone_date: str | None) -> dict[str, Any]:
    total = len(tasks)
    complete_statuses = {"done", "closed", "complete", "resolved"}
    blocked_statuses = {"blocked"}
    in_progress_statuses = {"in progress", "in review", "in development"}

    complete = sum(1 for t in tasks if t["status"].lower() in complete_statuses)
    blocked = sum(
        1
        for t in tasks
        if t["status"].lower() in blocked_statuses or t.get("blocker")
    )
    in_progress = sum(1 for t in tasks if t["status"].lower() in in_progress_statuses)
    percent_complete = round((complete / total) * 100, 1) if total else 0.0

    days_to_milestone = None
    if milestone_date:
        try:
            milestone = date.fromisoformat(milestone_date)
            days_to_milestone = (milestone - date.today()).days
        except ValueError:
            days_to_milestone = None

    return {
        "total_tasks": total,
        "complete": complete,
        "in_progress": in_progress,
        "blocked": blocked,
        "percent_complete": percent_complete,
        "days_to_milestone": days_to_milestone,
    }


def load_csv_tasks(
    csv_path: Path,
    platforms: list[dict[str, Any]],
    field_mapping: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    aliases = field_mapping.get("csv", {}).get("aliases", {})
    warnings: list[str] = []
    tasks: list[dict[str, Any]] = []

    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            platform_raw = resolve_csv_column(row, "platform", aliases)
            platform_id = match_platform(platform_raw, platforms)
            if not platform_id:
                warnings.append(f"Skipped row with unknown platform: {platform_raw!r}")
                continue

            task = {
                "platform": platform_id,
                "id": resolve_csv_column(row, "id", aliases),
                "title": resolve_csv_column(row, "title", aliases),
                "owner": resolve_csv_column(row, "owner", aliases) or "",
                "status": resolve_csv_column(row, "status", aliases) or "",
                "priority": resolve_csv_column(row, "priority", aliases) or "",
                "target_date": parse_date(resolve_csv_column(row, "target_date", aliases)),
                "blocker": parse_bool(resolve_csv_column(row, "blocker", aliases)),
                "epic": resolve_csv_column(row, "epic", aliases),
                "blocker_reason": resolve_csv_column(row, "blocker_reason", aliases),
                "updated_at": parse_date(resolve_csv_column(row, "updated_at", aliases)),
            }

            platform_cfg = next(p for p in platforms if p["id"] == platform_id)
            for field in platform_cfg.get("extra_fields", []):
                task[field] = resolve_csv_column(row, field, aliases)

            tasks.append(task)

    return tasks, warnings


def load_milestones(csv_path: Path) -> list[dict[str, Any]]:
    if not csv_path.exists():
        return []

    milestones: list[dict[str, Any]] = []
    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            name = row.get("name") or row.get("Name") or ""
            date_value = row.get("date") or row.get("Date") or ""
            platform = row.get("platform") or row.get("Platform") or "all"
            if not name or not date_value:
                continue
            milestones.append(
                {
                    "name": name.strip(),
                    "date": parse_date(date_value.strip()),
                    "platform": platform.strip().lower(),
                }
            )
    milestones.sort(key=lambda item: item["date"] or "")
    return milestones


def fetch_jira_tasks(
    platforms: list[dict[str, Any]],
    field_mapping: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    base_url = os.environ.get(field_mapping["jira"]["base_url_env"], "").rstrip("/")
    email = os.environ.get(field_mapping["jira"]["email_env"], "")
    token = os.environ.get(field_mapping["jira"]["token_env"], "")
    jql = os.environ.get(
        field_mapping["jira"]["jql_env"],
        field_mapping["jira"]["default_jql"],
    )

    if not all([base_url, email, token]):
        raise RuntimeError(
            "Jira mode requires JIRA_BASE_URL, JIRA_EMAIL, and JIRA_API_TOKEN env vars."
        )

    try:
        import urllib.error
        import urllib.parse
        import urllib.request
    except ImportError as exc:
        raise RuntimeError("urllib is unavailable") from exc

    auth_header = (
        "Basic "
        + __import__("base64").b64encode(f"{email}:{token}".encode()).decode()
    )
    headers = {
        "Accept": "application/json",
        "Authorization": auth_header,
    }

    jira_cfg = field_mapping["jira"]
    platform_field = jira_cfg.get("platform_field", "customfield_10111")
    fetch_fields = jira_cfg.get(
        "fetch_fields",
        ["summary", "status", "assignee", "priority", "duedate", "updated", "components", platform_field],
    )

    issues: list[dict[str, Any]] = []
    next_page_token: str | None = None
    while True:
        params: dict[str, Any] = {
            "jql": jql,
            "maxResults": 100,
            "fields": ",".join(fetch_fields),
        }
        if next_page_token:
            params["nextPageToken"] = next_page_token

        query = urllib.parse.urlencode(params)
        url = f"{base_url}/rest/api/3/search/jql?{query}"
        request = urllib.request.Request(url, headers=headers)

        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode() if exc.fp else ""
            raise RuntimeError(f"Jira API error: {exc.code} {exc.reason} {detail}") from exc

        issues.extend(payload.get("issues", []))
        if payload.get("isLast", True):
            break
        next_page_token = payload.get("nextPageToken")
        if not next_page_token:
            break

    tasks: list[dict[str, Any]] = []

    for issue in issues:
        fields = issue.get("fields", {})
        platform_id = resolve_jira_platform(issue, fields, platforms, platform_field)
        if not platform_id:
            warnings.append(
                f"Skipped Jira issue {issue.get('key')} — no matching platform group/component"
            )
            continue

        assignee = fields.get("assignee") or {}
        status = (fields.get("status") or {}).get("name", "To Do")
        priority = (fields.get("priority") or {}).get("name", "Medium")

        tasks.append(
            {
                "platform": platform_id,
                "id": issue.get("key", ""),
                "title": fields.get("summary", ""),
                "owner": assignee.get("displayName", "Unassigned"),
                "status": status,
                "priority": priority,
                "target_date": parse_date(fields.get("duedate") or ""),
                "blocker": status.lower() == "blocked",
                "epic": "",
                "blocker_reason": "",
                "updated_at": parse_date((fields.get("updated") or "")[:10]),
            }
        )

    return tasks, warnings


def build_recent_activity(tasks: list[dict[str, Any]], window_days: int = 7) -> list[dict[str, Any]]:
    cutoff = date.today().toordinal() - window_days
    activity: list[dict[str, Any]] = []
    for task in tasks:
        updated = task.get("updated_at")
        if not updated:
            continue
        try:
            updated_date = date.fromisoformat(updated)
        except ValueError:
            continue
        if updated_date.toordinal() >= cutoff:
            activity.append(
                {
                    "date": updated,
                    "id": task["id"],
                    "title": task["title"],
                    "change": f"Updated — status: {task['status']}",
                    "platform": task["platform"],
                }
            )
    activity.sort(key=lambda item: item["date"], reverse=True)
    return activity


def extract_resources(layout: dict[str, Any]) -> list[dict[str, str]]:
    for section in layout.get("sections", []):
        if section.get("type") == "links":
            return section.get("links", [])
    return []


def build_dashboard_payload(
    tasks: list[dict[str, Any]],
    milestones: list[dict[str, Any]],
    platforms: list[dict[str, Any]],
    layout: dict[str, Any],
    platform_filter: str | None = None,
) -> dict[str, Any]:
    if platform_filter:
        tasks = [task for task in tasks if task["platform"] == platform_filter]
        platforms = [p for p in platforms if p["id"] == platform_filter]
        milestones = [
            milestone
            for milestone in milestones
            if milestone.get("platform") in {platform_filter, "all"}
        ]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for task in tasks:
        grouped[task["platform"]].append(task)

    next_milestone_date = milestones[0]["date"] if milestones else None
    rollup_stats = compute_stats(tasks, next_milestone_date)

    platform_sections: dict[str, Any] = {}
    for platform in platforms:
        platform_id = platform["id"]
        platform_tasks = grouped.get(platform_id, [])
        platform_sections[platform_id] = {
            "label": platform["label"],
            "stats": compute_stats(platform_tasks, next_milestone_date),
            "tasks": sorted(
                platform_tasks,
                key=lambda t: (
                    layout.get("priority_order", []).index(t["priority"])
                    if t["priority"] in layout.get("priority_order", [])
                    else 99,
                    t.get("target_date") or "9999-12-31",
                ),
            ),
            "extra_fields": platform.get("extra_fields", []),
        }

    blockers = [
        {
            "platform": task["platform"],
            "id": task["id"],
            "title": task["title"],
            "owner": task["owner"],
            "status": task["status"],
            "blocker_reason": task.get("blocker_reason") or "Blocked",
            "target_date": task.get("target_date"),
        }
        for task in tasks
        if task.get("blocker") or task["status"].lower() == "blocked"
    ]

    window_days = 7
    for section in layout.get("sections", []):
        if section.get("id") == "recent_activity":
            window_days = section.get("window_days", 7)

    summary_label = "Overall Summary"
    for section in layout.get("sections", []):
        if section.get("type") == "stat_row":
            summary_label = section.get("label", summary_label)
            break

    return {
        "title": layout.get("title", "Promo CTA Project Dashboard"),
        "subtitle": layout.get("subtitle", ""),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "single_platform": layout.get("single_platform", False),
        "summary_label": summary_label,
        "data_note": (
            "Android-only dashboard using the shared references: GCX-122275, PLAY-122964, "
            "and the two Confluence pages. Jira fields will populate once credentials are configured."
            if platform_filter == "android"
            else None
        ),
        "resources": extract_resources(layout),
        "rollup": rollup_stats,
        "platforms": platform_sections,
        "milestones": milestones,
        "blockers": blockers,
        "recent_activity": build_recent_activity(tasks, window_days),
        "status_colors": layout.get("status_colors", {}),
        "priority_order": layout.get("priority_order", []),
        "warnings": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        choices=["csv", "jira"],
        default="csv",
        help="Data source (default: csv)",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_TASKS_CSV,
        help="CSV file path when --source csv",
    )
    parser.add_argument(
        "--milestones",
        type=Path,
        default=DEFAULT_MILESTONES_CSV,
        help="Milestones CSV path",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output JSON path",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON",
    )
    parser.add_argument(
        "--layout",
        type=Path,
        default=CONFIG_DIR / "dashboard-layout.yaml",
        help="Dashboard layout YAML path",
    )
    parser.add_argument(
        "--platform",
        help="Filter to a single platform id (apple, android, lightbeam, roku)",
    )
    args = parser.parse_args()

    load_env_file()

    platforms_cfg = load_yaml(CONFIG_DIR / "platforms.yaml")
    layout_cfg = load_yaml(args.layout)
    mapping_cfg = load_yaml(CONFIG_DIR / "field-mapping.yaml")

    platforms = platforms_cfg.get("platforms", [])
    platform_filter = args.platform or layout_cfg.get("platform_filter")

    if args.source == "csv":
        if not args.input.exists():
            print(f"CSV not found: {args.input}", file=sys.stderr)
            return 1
        tasks, warnings = load_csv_tasks(args.input, platforms, mapping_cfg)
    else:
        tasks, warnings = fetch_jira_tasks(platforms, mapping_cfg)

    milestones = load_milestones(args.milestones)
    payload = build_dashboard_payload(
        tasks,
        milestones,
        platforms,
        layout_cfg,
        platform_filter=platform_filter,
    )
    payload["warnings"] = warnings

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2 if args.pretty else None)
        handle.write("\n")

    print(f"Wrote {len(tasks)} tasks to {args.output}")
    if warnings:
        print(f"Warnings ({len(warnings)}):", file=sys.stderr)
        for warning in warnings[:10]:
            print(f"  - {warning}", file=sys.stderr)
        if len(warnings) > 10:
            print(f"  ... and {len(warnings) - 10} more", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
