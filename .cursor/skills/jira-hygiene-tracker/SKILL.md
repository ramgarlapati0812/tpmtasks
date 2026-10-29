---
name: jira-hygiene-tracker
description: Audits GCX Epic hygiene (Lead TPM, dates, fix versions, Hard Deadline tag) using the GCX audit JQL and six execution rules from Confluence. Use when the user asks for Jira hygiene, hygiene tracker, missing required fields, or GCX Epic field gaps.
---

# Jira Hygiene Tracker Skill

Audit **GCX Epics** for **Fields to Track Jira Hygine through execution** per GCX Confluence. Rules, audit JQL, and TPM roster are in [`reference.md`](reference.md).

## When to use

Trigger this skill when the user asks to:

- Run a **Jira hygiene** or **hygiene tracker** audit
- Find Epics **missing required fields** (Lead TPM, Target Delivery Date, Fix versions, Desired Date)
- Check **P0** hygiene (Rules 2, 5, 6)
- Report gaps for GCX TPM epics (`2026-Q4` scope in default JQL)

## Source of truth

| Item | Value |
|------|--------|
| Confluence | https://wbdstreaming.atlassian.net/wiki/spaces/GCX/pages/3818556096/Jira+hygine+tracker+Fields |
| Page ID | `3818556096` |
| In-repo rules | [`reference.md`](reference.md) |

If Confluence differs from `reference.md`, prefer **Confluence** and update `reference.md`.

## Prerequisites

1. **Atlassian MCP** authenticated (`mcp_auth` on namespace `Atlassian` if needed).
2. `GetDynamicTools` for namespace `Atlassian` before Jira/Confluence calls.
3. Resolve `cloudId` once per run.

## Workflow

### 1. Load rules

1. Read [`reference.md`](reference.md) for audit JQL, six rules, P0 priority, TPM list, and field names.
2. Optionally refresh from Confluence: `getConfluenceContent(content_id="3818556096", content_format="markdown", detail="full")` and reconcile `reference.md`.

### 2. Run audit JQL

Use the **Audit JQL** from `reference.md` (default quarter `cf[10113] = 2026-Q4`). Override only when the user specifies another quarter or filter.

```jql
type = "Epic" AND status NOT IN (Done, Cancelled, "Ready for Release") AND cf[10111] IN ("GCX Android", "GCX APPLE", "GCX CDEV", "GCX Dotcom", "GCX LIGHTBEAM", "GCX ROKU", "GCX WEB", "GCX DWT Design Workflow and Tooling") AND cf[10113] = 2026-Q4 AND "Enabler[Dropdown]" != Bugs AND ("Target Release[Select List (multiple choices)]" NOT IN ("Tech Excellence Next Up", "Operational Excellence Next Up") or labels = tech-cross-platform)
```

Call `searchJiraIssuesUsingJql` with fields needed for all rules (see `reference.md`). Paginate until complete.

### 3. Evaluate rules per issue

For each Epic, evaluate Rules 1–6 from `reference.md`:

| Rule | Field | P0 |
|------|-------|-----|
| 1 | Lead TPM | |
| 2 | Target Delivery Date | Yes |
| 3 | Fix versions | |
| 4 | Desired Date vs Target Delivery Date | |
| 5 | Status (`New`/`Define` vs Desired Date within 5 weeks) | Yes |
| 6 | Tag = Hard Deadline → Desired Date required | Yes |

Record **failed rule numbers** and human-readable **missing fields / violations** (not only empty fields — include date ordering and Rule 5 status lag).

**Date math:** Use the user’s timezone for “today”; “5 weeks” = today + 35 calendar days unless Jira/site policy says otherwise.

**Tags/labels:** Treat **Hard Deadline** as documented on the page (label or Tag field — match however it appears on the issue).

### 4. Report results

**Summary:**

```markdown
# Jira hygiene report

- **JQL:** [audit JQL used]
- **Issues scanned:** N
- **Issues with any failure:** M
- **P0 failures (Rules 2, 5, 6):** K
- **Generated:** [timestamp, user timezone]
```

**Per-issue table:**

| Issue key | Summary | Status | Priority | Assignee | Lead TPM | Failed rules | P0? | Violations |
|-----------|---------|--------|----------|----------|----------|--------------|-----|------------|

- **Failed rules:** comma-separated rule numbers (e.g. `2, 5`)
- **Violations:** short text (e.g. `Target Delivery Date empty`, `Desired Date before Target Delivery Date`, `New with Desired Date within 5 weeks`)

**Optional:** group by assignee or Lead TPM; add TPM roster from `reference.md` when reporting team-wide hygiene.

### 5. Quality checks

- [ ] Audit JQL matches `reference.md` unless user changed scope
- [ ] All six rules applied; P0 called out
- [ ] No rules invented beyond Confluence / `reference.md`
- [ ] Confluence re-fetched when user says rules changed

## Atlassian MCP quick reference

| Goal | Typical tool |
|------|----------------|
| Jira search | `searchJiraIssuesUsingJql` |
| Single issue | `getJiraIssue` |
| Confluence page | `getConfluenceContent` |

## Additional resources

- Rules, JQL, TPM list: [`reference.md`](reference.md)
