#!/usr/bin/env python3
"""Evaluate GCX EPIC hygiene rules deterministically.

Usage:
  python evaluate.py --pages page1.json [page2.json ...] --config config.json \
      --today 2026-10-15 --outdir ./out

Inputs
  --pages   One or more raw Jira search results (the JSON returned by
            searchJiraIssuesUsingJql, or the saved tool-result file). Each has
            issues.nodes[].fields.
  --config  Rule parameters read from the wiki rules page (see SKILL.md).
  --today   Run date, YYYY-MM-DD (use the sandbox `date`, never guess).

Outputs (in --outdir)
  results.json         per-EPIC evaluation (for audit/debugging)
  confluence_body.html body for the Confluence report page
  summary.json         per-TPM P0 counts
  payload.json         ready-to-send payload for the send-report-summary skill
                       (subject, intro, wiki link all dated with --today)
  Also prints a short verification block to stdout.
"""
import argparse, collections, datetime, html, json, os, sys

DEFAULT_FIELDS = {
    "tpm": "customfield_10065",       # Lead TPM (user)
    "tdd": "customfield_13254",       # Target Delivery Date (option, date in .value)
    "desired": "customfield_10066",   # Desired Date (date string)
    "tags": "customfield_13722",      # Tags (array of options)
}

RULE_LABELS = {
    "R1": "Rule 1: Lead TPM empty",
    "R2": "Rule 2: Target Delivery Date empty",
    "R3": "Rule 3: Fix Versions empty",
    "R4": "Rule 4: Desired Date before Target Delivery Date",
    "R5": "Rule 5: New/Define, Desired Date < 5 weeks out",
    "R6": "Rule 6: Hard Deadline, no Desired Date",
}


def _nodes(data):
    """Return the list of issues from either connector format."""
    if isinstance(data, list):
        return data
    if "issues" in data:
        iss = data["issues"]
        return iss["nodes"] if isinstance(iss, dict) else iss      # old: issues.nodes[]  | new: issues[]
    if "data" in data:
        return _nodes(data["data"])                                  # new connector wraps in data{}
    if "nodes" in data:
        return data["nodes"]
    sys.exit("Unrecognised Jira result format (expected issues.nodes[], data.issues[] or issues[])")


def load_issues(paths):
    seen, issues = set(), []
    for p in paths:
        for n in _nodes(json.load(open(p))):
            if n["key"] in seen:
                sys.exit(f"Duplicate EPIC key across pages: {n['key']}")
            seen.add(n["key"])
            issues.append(n)
    return issues


def _field(f, fid):
    """Raw value of a custom field from either format: raw customfield_* key, or
    customFields{<label>: {id, value}} (the value is absent when the field is empty)."""
    if fid in f:
        return f[fid]
    for entry in (f.get("customFields") or {}).values():
        if isinstance(entry, dict) and entry.get("id") == fid:
            return entry.get("value")
    return None


def _scalar(v):
    """Descend through {'value': ...} wrappers to the underlying scalar (dates, option names)."""
    while isinstance(v, dict) and "value" in v:
        v = v["value"]
    return v


def parse(issue, F, fv_empty):
    f = issue["fields"]
    tpm_raw = _field(f, F["tpm"])
    tpm = tpm_raw.get("displayName") if isinstance(tpm_raw, dict) else None
    tdd = _scalar(_field(f, F["tdd"]))
    desired = _scalar(_field(f, F["desired"]))
    tags_raw = _field(f, F["tags"]) or []
    if isinstance(tags_raw, dict):
        tags_raw = [tags_raw]
    tags = [_scalar(t) for t in tags_raw]
    if "fixVersions" in f:
        fix_versions = [v.get("name") for v in (f.get("fixVersions") or [])]
    elif fv_empty is not None:
        fix_versions = [] if issue["key"] in fv_empty else ["(set)"]
    else:
        sys.exit("This connector does not return fixVersions. Run the 'fixVersion is EMPTY' query and pass it with --fv-empty.")
    return {
        "key": issue["key"],
        "status": (f.get("status") or {}).get("name"),
        "tpm": tpm,
        "tdd": tdd or None,
        "desired": desired or None,
        "tags": tags,
        "fix_versions": fix_versions,
    }


def evaluate(e, cfg, today, cutoff):
    s = e["status"]
    S = lambda k: set(cfg["statuses"][k])
    fails = []  # (rule_id, text)
    if not e["tpm"]:
        fails.append(("R1", "Lead TPM (empty)"))
    if s in S("R2") and not e["tdd"]:
        fails.append(("R2", "Target Delivery Date (empty)"))
    if s in S("R3") and not e["fix_versions"]:
        fails.append(("R3", "Fix Versions (empty)"))
    if s in S("R4") and e["desired"] and e["tdd"] and e["desired"] < e["tdd"]:
        fails.append(("R4", f"Desired Date {e['desired']} before Target Delivery Date {e['tdd']}"))
    # Rule 5: New/Define and Desired Date earlier than today + rule5_weeks (empty Desired Date not failed; Rule 6 covers it)
    if s in S("R5") and e["desired"] and e["desired"] < cutoff.isoformat():
        fails.append(("R5", f"Status {s} with Desired Date {e['desired']} less than {cfg['rule5_weeks']} weeks from today"))
    if s in S("R6") and cfg["hard_deadline_tag"] in e["tags"] and not e["desired"]:
        fails.append(("R6", "Desired Date (empty, Tag = Hard Deadline)"))
    p0 = set(cfg["p0_rules"])
    e["fails"] = [{"rule": r, "text": t + (" [P0]" if r in p0 else ""), "p0": r in p0} for r, t in fails]
    e["failed"] = bool(fails)
    e["p0_failed"] = any(x["p0"] for x in e["fails"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", nargs="+", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--today", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--fv-empty", help="Jira result listing EPICs whose Fix Versions are EMPTY "
                    "(needed when the connector omits fixVersions)")
    ap.add_argument("--expect", help='JSON of counts taken from Jira count queries, e.g. '
                    '{"total":150,"R1":16,"R2":12}; the run aborts if the script disagrees')
    a = ap.parse_args()

    cfg = json.load(open(a.config))
    F = {**DEFAULT_FIELDS, **cfg.get("fields", {})}
    today = datetime.date.fromisoformat(a.today)
    cutoff = today + datetime.timedelta(weeks=cfg["rule5_weeks"])

    fv_empty = {n["key"] for n in _nodes(json.load(open(a.fv_empty)))} if a.fv_empty else None
    epics = [parse(i, F, fv_empty) for i in load_issues(a.pages)]
    for e in epics:
        evaluate(e, cfg, today, cutoff)

    groups = collections.defaultdict(list)
    for e in epics:
        groups[e["tpm"] or "Unassigned"].append(e)
    order = sorted(groups, key=lambda t: (-sum(x["failed"] for x in groups[t]), t.lower()))

    total = len(epics)
    failed = sum(e["failed"] for e in epics)
    p0_total = sum(e["p0_failed"] for e in epics)
    p0_rules = [r for r in ["R1", "R2", "R3", "R4", "R5", "R6"] if r in set(cfg["p0_rules"])]

    # ---- Confluence body (no JQL, no P0 rule list, no footer) ----
    h = [f"<h1>{html.escape(cfg['report_title'])}</h1>",
         f"<p><strong>Run Date:</strong> <time datetime=\"{a.today}\">{today.strftime('%B')} {today.day}, {today.year}</time><br/>"
         f"<strong>Total Epics Scanned:</strong> {total}<br/><strong>Epics Failing Hygiene:</strong> {failed}</p>"]
    for t in order:
        fl = [x for x in groups[t] if x["failed"]]
        h.append(f"<h2>{html.escape(t)}</h2><ul><li><p>Total EPICs assigned: {len(groups[t])}</p></li><li><p>Failed: {len(fl)}</p></li></ul>")
        if not fl:
            h.append("<p>No hygiene failures detected.</p>")
            continue
        rows = "".join(
            f"<tr><td><p><a href=\"{cfg['jira_base']}/browse/{x['key']}\">{x['key']}</a></p></td>"
            f"<td><p>{html.escape(x['status'] or '')}</p></td>"
            f"<td><p>{html.escape('; '.join(f['text'] for f in x['fails']))}</p></td></tr>" for x in fl)
        h.append("<table><thead><tr><th><p>Epic Key</p></th><th><p>Status</p></th><th><p>Failed Fields</p></th></tr></thead>"
                 f"<tbody>{rows}</tbody></table>")
    os.makedirs(a.outdir, exist_ok=True)
    open(os.path.join(a.outdir, "confluence_body.html"), "w").write("".join(h))

    # ---- summary payload for the send skill ----
    p0_rows = []
    for t in order:
        g = groups[t]
        n = sum(x["p0_failed"] for x in g)
        if n:
            by = {r: sum(any(f["rule"] == r for f in x["fails"]) for x in g) for r in p0_rules}
            p0_rows.append({"name": "Unassigned (no Lead TPM)" if t == "Unassigned" else t, "p0": n, "by_rule": by})
    p0_rows.sort(key=lambda r: (-r["p0"], r["name"].lower()))
    col_ids = p0_rules
    summary = {
        "run_date": a.today,
        "total": total, "failed": failed, "p0_total": p0_total,
        "columns": ["Lead TPM", "EPICs failing a P0 rule"] + [RULE_LABELS[r] for r in col_ids],
        "rows": [[r["name"], r["p0"]] + [r["by_rule"][c] for c in col_ids] for r in p0_rows],
        "total_row": ["Total", p0_total] + [sum(r["by_rule"][c] for r in p0_rows) for c in col_ids],
    }
    json.dump(summary, open(os.path.join(a.outdir, "summary.json"), "w"), indent=2)

    # Ready-to-send payload for the send-report-summary skill. Every date comes from
    # --today (the day the report is generated), so nothing is ever typed by hand.
    qlabel = cfg.get("quarter_label", "Q3")
    page_url = (cfg.get("report_page_url_base",
                        "https://wbdstreaming.atlassian.net/wiki/spaces/GCX/pages/3874751281/Feature+Execution+Audit+Report")
                + f"+{a.today}")
    payload = {
        "subject": f"Jira Audit Report for {qlabel} Features as on - {today.strftime('%b')} {today.day}, {today.year}",
        "intro": (f"Of the {total} EPICs audited, {failed} need attention. Among them, {p0_total} EPICs listed below "
                  "fail at least one P0 rule. Please review the wiki and fix your flagged EPICs by end of this week."),
        "link": {"prefix": "Wiki", "label": f"Feature Execution Audit Report {a.today}", "url": page_url},
        "table": {"title": "Failed EPICs per TPM — P0 rules only", "columns": summary["columns"],
                  "rows": summary["rows"], "total_row": summary["total_row"]},
        "recipients": cfg.get("recipients", ["sahana.hebbar@wbd.com"]),
        "channel": "email",
    }
    json.dump(payload, open(os.path.join(a.outdir, "payload.json"), "w"), indent=2)
    json.dump(epics, open(os.path.join(a.outdir, "results.json"), "w"), indent=2)

    # ---- cross-check against independent Jira count queries ----
    if a.expect:
        want = json.loads(a.expect)
        got = {"total": total}
        for r in ("R1", "R2", "R3", "R5", "R6"):
            got[r] = sum(any(f["rule"] == r for f in e["fails"]) for e in epics)
        bad = {k: (want[k], got[k]) for k in want if k in got and want[k] != got[k]}
        if bad:
            sys.exit(f"CROSS-CHECK FAILED (Jira count vs script count): {bad}. Do not publish; the data was likely copied incorrectly.")
        print("Cross-check vs Jira counts: OK", {k: got[k] for k in want if k in got})

    # ---- verification block ----
    assert sum(len(v) for v in groups.values()) == total
    assert sum(r["p0"] for r in p0_rows) == p0_total
    print(f"EPICs: {total} | failing any rule: {failed} | failing a P0 rule: {p0_total}")
    print(f"Rule 5: Desired Date must be >= {cutoff} (today {today} + {cfg['rule5_weeks']} weeks)")
    print("Per-rule failure counts:", dict(collections.Counter(f['rule'] for e in epics for f in e['fails'])))
    for t in order:
        g = groups[t]
        print(f"  {t}: total {len(g)}, failed {sum(x['failed'] for x in g)}, P0 {sum(x['p0_failed'] for x in g)}")
    print("Sums check: OK")


if __name__ == "__main__":
    main()
