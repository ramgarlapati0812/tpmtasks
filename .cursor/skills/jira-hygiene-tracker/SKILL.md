---
name: jira-hygiene-tracker
description: Audits Jira issues for missing hygiene-tracker required fields per GCX Confluence. Use when the user asks for Jira hygiene, missing required fields, hygiene tracker, field completeness, or GCX Jira field gaps.
---

# Jira Hygiene Tracker Skill

Find Jira issues that are **missing required fields** for the **Jira hygiene tracker**, using rules documented on Confluence (GCX space). Do not guess field names or JQL — load them from the page (and linked pages) on each run.

## When to use

Trigger this skill when the user asks to:

- Run a **Jira hygiene** or **hygiene tracker** audit
- List issues **missing required fields**
- Check **field completeness** for GCX / WBD streaming Jira work
- Report **gaps** before sprint review, planning, or status reporting

## Source of truth

| Item | Value |
|------|--------|
| Confluence space | GCX |
| Page title | Jira hygine tracker Fields |
| Page URL | https://wbdstreaming.atlassian.net/wiki/spaces/GCX/pages/3818556096/Jira+hygine+tracker+Fields |
| Page ID (`content_id`) | `3818556096` |

If the live page and [`reference.md`](reference.md) disagree, **the live Confluence page wins**.

## Prerequisites

1. **Atlassian MCP** authenticated (`CallDynamicTool` → namespace `Atlassian` → `mcp_auth` if needed).
2. Discover tools with `GetDynamicTools` for namespace `Atlassian` before calling them.
3. Resolve `cloudId` once per run (from an Atlassian tool that lists sites/clouds, or from search results).

## Workflow

### 1. Load field rules from Confluence

1. Fetch the canonical page as markdown:
   - Tool pattern: `getConfluenceContent(cloudId, content_id="3818556096", content_format="markdown", detail="full")`
   - Invoke via `CallDynamicTool` with the exact tool name/schema from `GetDynamicTools`.
2. Parse the page for:
   - **Required fields** (display name, custom field ID if listed, issue types / statuses where rules apply)
   - **Optional vs required** distinctions and any **conditional** rules (e.g. only for Bugs, only when In Progress)
   - **Project keys**, **issue types**, **workflows**, or **status** scopes
   - **JQL** snippets or filter definitions provided on the page
3. **Linked pages**: for each Confluence link referenced for extra rules (field definitions, hygiene process, JQL libraries), fetch with `getConfluenceContent` using that page’s ID from the URL (`/pages/<id>/`).
4. **Update local cache (optional but recommended):** merge parsed rules into [`reference.md`](reference.md) with a “Last synced from Confluence” line (date + page version if available). Never add fields to `reference.md` that are not on Confluence.

If Confluence cannot be read, **stop** and tell the user to connect Atlassian MCP or paste the page content. Do not invent field IDs or required-field lists.

### 2. Build the hygiene checklist

From the parsed doc only, produce an internal checklist:

```text
For each rule:
  - field_key or customfield_XXXXX (if documented)
  - human-readable name
  - scope: projects / issue types / statuses
  - empty means: null, unset, "None", placeholder, or doc-defined invalid values
```

Respect any doc-specific definitions of “filled” (e.g. Epic Link required for Stories but not Tasks).

### 3. Query Jira for candidates

1. Start from **JQL on the Confluence page**. If none is given, ask the user for project/scope or use the narrowest JQL the page implies (e.g. single project key named on the page).
2. Run search via Atlassian MCP, e.g. `searchJiraIssuesUsingJql(cloudId, jql, fields=[...])`, requesting at minimum:
   - `key`, `summary`, `status`, `priority`, `assignee`, `issuetype`, `project`
   - Every field ID/name from the hygiene checklist
3. Paginate until the JQL result set is exhausted (respect tool `maxResults` / cursor limits).

### 4. Detect gaps

For each issue:

1. Apply only rules whose **scope** matches (project, issue type, status).
2. Mark a field **missing** when empty per the Confluence definition.
3. Collect `missing_fields` as stable identifiers (prefer `customfield_XXXXX` when documented, else exact Jira field name from the page).

### 5. Report results

Deliver a structured report (markdown table or canvas for large sets).

**Summary block:**

```markdown
# Jira hygiene report

- **Scope:** [JQL used]
- **Rules source:** [Confluence page 3818556096 + linked page titles]
- **Issues scanned:** N
- **Issues with gaps:** M
- **Generated:** [timestamp, user timezone]
```

**Per-issue table (required columns):**

| Issue key | Summary | Status | Priority | Assignee | Missing fields |
|-----------|---------|--------|----------|----------|----------------|
| PROJ-123 | … | In Progress | High | Name | Field A, customfield_10001 |

**Optional groupings** (when useful):

- By assignee (who needs to fix the most gaps)
- By missing field (systemic gaps)
- By priority / status

**Quality checks before sending:**

- [ ] Every “missing” field appears on the Confluence-derived checklist
- [ ] JQL and scope match the documentation (no extra projects/issue types unless user asked)
- [ ] Linked Confluence pages were fetched when the main page references them for field definitions
- [ ] No fabricated custom field IDs

## Atlassian MCP quick reference

Use `GetDynamicTools` for authoritative schemas. Common tools (names may vary slightly):

| Goal | Typical tool |
|------|----------------|
| Cross-system lookup | `search` (natural language query — not JQL/CQL) |
| Confluence by ID | `getConfluenceContent` |
| Confluence search | `searchConfluence` (CQL) |
| Jira search | `searchJiraIssuesUsingJql` (JQL) |
| Single issue | `getJiraIssue` |

Example Confluence CQL if ID fetch fails:

```text
space = GCX AND title ~ "Jira hygine tracker Fields"
```

## Related skills

- Company knowledge search patterns: Atlassian plugin skill `search-company-knowledge` (parallel search and fetch workflow).

## Additional resources

- Cached field catalog (sync from Confluence): [`reference.md`](reference.md)
