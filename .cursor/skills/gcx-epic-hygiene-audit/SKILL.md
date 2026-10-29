---
name: "gcx-epic-hygiene-audit"
description: "Run the weekly GCX Jira EPIC hygiene audit. Reads the audit JQL, TPM list and hygiene rules from the Confluence wiki page, fetches the matching EPICs from Jira, evaluates every rule with a bundled script (so counts are exact and repeatable), groups failures by Lead TPM, updates the \"Feature Execution Audit Report\" Confluence page with today's date, and produces a P0 summary for the send-report-summary skill. Use this whenever the user mentions the Jira hygiene audit, EPIC hygiene, feature execution audit, GCX audit, \"run the audit\", Lead TPM failures, or the weekly Tuesday audit, even if they do not say \"skill\"."
---

# GCX EPIC Hygiene Audit

Why this exists: an LLM-only agent gave inconsistent results run to run. Here the judgement work (read the wiki, choose parameters) is done by you, and the counting is done by `scripts/evaluate.py`, so the same data always gives the same answer.

Everything that changes week to week lives on the wiki, not in this skill:
- Rules page: https://wbdstreaming.atlassian.net/wiki/x/wIqa4w (page id 3818556096, "Jira hygine tracker Fields")
- Report page that gets overwritten each run: https://wbdstreaming.atlassian.net/wiki/x/MQP05g (page id 3874751281)
- Atlassian site `wbdstreaming.atlassian.net`, cloudId `d10cfe0e-39b2-4333-a28b-1edc39bbb969`

Get today's date from bash (`date +%F`); never guess it.

## Modes
- **Full run** (default for scheduled runs): steps 1-6.
- **Dry run** (when the user or a test says "dry run", "don't publish", or "test"): do steps 1-4 and 6, skip the Confluence write in step 5, and say that nothing was published.

## Step 1. Read the rules page
Fetch the rules page as HTML. It contains the **Audit JQL**, the **TPM list**, **Rules 1-6** (FAIL/PASS conditions with status lists) and a **Rule Priority** section naming the P0 rules. Decode HTML entities (`&quot;` becomes `"`). If a rule was added, removed or reworded in a way the script cannot express (see step 3), stop and tell the user what changed instead of guessing.

## Step 2. Fetch the EPICs
Run the JQL **exactly as written**: no edits, no extra filters (never filter by user, assignee, reporter or Lead TPM). Use the Atlassian connector's `searchJiraIssuesUsingJql` with `cloudId` `d10cfe0e-39b2-4333-a28b-1edc39bbb969`, `fields = ["status","customfield_10065","customfield_13254","customfield_10066","customfield_13722","fixVersions"]`, `maxResults = 100`, and follow `nextPageToken` until the last page (`hasNextPage` false or `isLast` true).

Field map: Lead TPM `customfield_10065` (user), Target Delivery Date `customfield_13254`, Desired Date `customfield_10066`, Tags `customfield_13722`, Lead Engineer `customfield_10067` (only if the rules page uses it again).

**Two connector formats exist** and `evaluate.py` reads both: the older one (`issues.nodes[]` with raw `customfield_*` keys) and the newer one (`data.issues[]` with fields under `customFields`, labelled by name, empty fields carrying only an `id`). Do not convert anything by hand.

**Getting the pages into files.** Large pages are saved by the tool to a file and it prints the path: copy that file into the sandbox (under `/sessions/<session>/mnt/.claude/projects/session/*/tool-results/`; find it with `find / -name "mcp-*searchJiraIssuesUsingJql*" 2>/dev/null`). Small pages (typically the last one) come back inline instead. Save an inline page to a file with an exact, unedited copy of the returned JSON; do not summarize, reorder or "fix" anything. Step 3's cross-check against Jira's own counts is what proves nothing was lost or altered in the copy.

**Fix Versions.** Some connector versions do not return `fixVersions` at all. If it is missing, also run `(<the Audit JQL>) AND fixVersion is EMPTY` with `fields=["status"]` and save that result to a file; it lists the EPICs with no Fix Version, and the script uses it for Rule 3 (pass it with `--fv-empty`).

**Count cross-check (do this every run).** Using `searchResultMode = "count"`, get Jira's own counts for these queries (wrap the Audit JQL in parentheses and add the clause):
- `total`: the Audit JQL as is
- `R1`: `(<JQL>) AND cf[10065] is EMPTY`
- `R2`: `(<JQL>) AND status IN (<R2 statuses>) AND cf[13254] is EMPTY`
- `R3`: `(<JQL>) AND status IN (<R3 statuses>) AND fixVersion is EMPTY`
Pass them to the script as `--expect '{"total":N,"R1":n,"R2":n,"R3":n}'`. If the script reports a mismatch, stop and report it: it means the data was copied wrongly or Jira changed mid-run, and a wrong report is worse than none.

If the JQL errors or returns zero EPICs, stop and report it. A silent empty report is worse than no report.

## Step 3. Evaluate with the script
Write `config.json` from the rules page (copy status lists exactly as the wiki gives them):

```json
{
  "report_title": "GCX Q4 2026 Jira Hygiene Audit",
  "quarter_label": "Q4",
  "recipients": ["sahana.hebbar@wbd.com"],
  "jira_base": "https://wbdstreaming.atlassian.net",
  "quarter_start": "2026-10-01",
  "rule5_weeks": 5,
  "hard_deadline_tag": "Hard Deadline",
  "p0_rules": ["R2", "R5", "R6"],
  "statuses": {
    "R2": ["Plan","Build","Ready to Test","Test","Ready for Release"],
    "R3": ["Plan","Build","Ready to Test","Test","Ready for Release"],
    "R4": ["Solutioning","Plan","Build","Ready to Test","Test","Ready for Release"],
    "R5": ["New","Define"],
    "R6": ["New","Define","Solutioning","Build","Ready to Test","Test","Ready for Release"]
  }
}
```

Take the quarter label and `quarter_start` from the JQL's `cf[10113] = 2026-Q4` value (Q1 Jan 1, Q2 Apr 1, Q3 Jul 1, Q4 Oct 1) and `p0_rules` from the Rule Priority section.

**Rule 5 patch (required, idempotent).** The bundled [`scripts/evaluate.py`](scripts/evaluate.py) in this repo already uses the **2026-10-29** Rule 5 logic (Desired Date vs today + `rule5_weeks`). If you copied an older script from elsewhere, it may still use quarter-week cutoff. Copy the script to a writable folder and patch the copy before running. Write this as `patch_rule5.py` and run `python3 -I patch_rule5.py <copy of evaluate.py>`; it prints "already patched" and exits if the script already has the new logic (in that case run [`scripts/evaluate.py`](scripts/evaluate.py) as is):

```python
import sys
p=sys.argv[1]; s=open(p).read()
if "rule5_weeks" in s and "today + " in s: sys.exit("already patched")
def r(a,b):
    global s
    assert a in s,a; s=s.replace(a,b)
r('"R5": "Rule 5: New/Define past week 3"','"R5": "Rule 5: New/Define, Desired Date < 5 weeks out"')
r('''    if s in S("R5") and today > cutoff:
        fails.append(("R5", f"Status {s} past week {cfg['rule5_weeks']} of quarter"))''','''    # Rule 5: New/Define and Desired Date earlier than today + rule5_weeks (empty Desired Date not failed; Rule 6 covers it)
    if s in S("R5") and e["desired"] and e["desired"] < cutoff.isoformat():
        fails.append(("R5", f"Status {s} with Desired Date {e['desired']} less than {cfg['rule5_weeks']} weeks from today"))''')
r('''    qstart = datetime.date.fromisoformat(cfg["quarter_start"])
    cutoff = qstart + datetime.timedelta(weeks=cfg["rule5_weeks"])''','''    cutoff = today + datetime.timedelta(weeks=cfg["rule5_weeks"])''')
r('print(f"Rule 5 cutoff date: {cutoff} (today {today})")','print(f"Rule 5: Desired Date must be >= {cutoff} (today {today} + {cfg[\'rule5_weeks\']} weeks)")')
open(p,'w').write(s)
```

Then run (using the patched copy of the script):

```bash
python3 -I <patched evaluate.py> --pages <page files> --config config.json --today <YYYY-MM-DD> --outdir out \
  [--fv-empty <fix-version-empty result file>] --expect '<json of Jira counts>'
```

What the script implements (and the interpretations agreed with the user):
- R1 Lead TPM empty fails (any status).
- R2 Target Delivery Date empty fails for the R2 statuses. R3 Fix Versions empty fails for the R3 statuses.
- R4 fails when Desired Date is before Target Delivery Date, only when both are set (an empty Desired Date is not failed here) and status is in R4 statuses.
- **R5 (updated 2026-10-29)** fails when status is New/Define AND Desired Date is set AND Desired Date is earlier than today + `rule5_weeks` weeks (5 weeks = 2.5 sprints needed to define, plan and execute). An empty Desired Date does not fail R5 (Rule 6 covers it); a Desired Date in the past does fail. PASS if status is not New/Define. The wiki's Rule 5 was updated to match; if the wiki wording changes again (for example the number of weeks), set `rule5_weeks` accordingly.
- R6 fails when status is in the R6 statuses, Tags contains "Hard Deadline", and Desired Date is empty.

The script prints a verification block (totals, per-rule counts, per-TPM counts, sum checks). Read it. If any check fails or a count looks implausible, investigate before publishing.

## Step 4. Review before publishing
Compare `out/summary.json` against what you'd expect (total matches the JQL count; failed and P0 counts are plausible). Note anything worth flagging to the user: Lead TPM names that are not on the wiki TPM list (compare case-insensitively; spelling variants such as "RAM GARLAPATI" vs "Ram Garlapati" or "GopalaKrishnan" vs "GopalKrishnan" are the same person), EPICs with no Lead TPM, and any wiki ambiguity.

## Step 5. Update the Confluence page (skip in dry run)
Call `getConfluenceContent` (detail = outline) on page id 3874751281 to get the current `snapshotToken`, then `updateConfluenceContent` with `body = {"format":"html","value": <contents of out/confluence_body.html>}`, `contentId = 3874751281`, and `title = "Feature Execution Audit Report YYYY-MM-DD"` using today's date. The same page is overwritten every run on purpose; Confluence version history keeps earlier runs. The body deliberately has no JQL, no P0 rule list and no footer. If the write fails (for example a 403), stop and report it; do not create other pages.

## Step 6. Hand off and report
`out/payload.json` is ready to give to the `send-report-summary` skill as is. The script builds the subject (`Jira Audit Report for Q4 Features as on - <Mon D, YYYY>`), the intro sentence, the wiki link and the P0 table, and every date in them is the date the report was generated (the `--today` value). Do not retype or edit the date by hand, and never reuse a date from an earlier run or an example. Recipients come from `recipients` in `config.json` (add `"recipients": ["sahana.hebbar@wbd.com"]` and `"quarter_label"` to the config; the default is Sahana only).

Finish with a short summary: counts, page link (or "dry run, not published"), and any flags from step 4. The report names individual employees, so never send it beyond the confirmed recipients.

