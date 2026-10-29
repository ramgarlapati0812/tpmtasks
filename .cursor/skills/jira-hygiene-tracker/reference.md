# Jira hygiene tracker — field catalog

**Confluence:** [Jira hygine tracker Fields](https://wbdstreaming.atlassian.net/wiki/spaces/GCX/pages/3818556096/Jira+hygine+tracker+Fields) (`content_id`: `3818556096`)

Re-fetch via Atlassian MCP when the page may have changed; this file is the in-repo cache for agents.

## Audit JQL

Use this JQL verbatim unless the user or Confluence specifies a different scope:

```jql
type = "Epic" AND status NOT IN (Done, Cancelled, "Ready for Release") AND cf[10111] IN ("GCX Android", "GCX APPLE", "GCX CDEV", "GCX Dotcom", "GCX LIGHTBEAM", "GCX ROKU", "GCX WEB", "GCX DWT Design Workflow and Tooling") AND cf[10113] = 2026-Q4 AND "Enabler[Dropdown]" != Bugs AND ("Target Release[Select List (multiple choices)]" NOT IN ("Tech Excellence Next Up", "Operational Excellence Next Up") or labels = tech-cross-platform)
```

### JQL field hints

| Reference in JQL | Notes |
|------------------|--------|
| `cf[10111]` | GCX team / portfolio dimension (values listed in audit JQL) |
| `cf[10113]` | Quarter (example value: `2026-Q4`) |
| `Enabler[Dropdown]` | Must not be `Bugs` |
| `Target Release[Select List (multiple choices)]` | Excludes two “Next Up” values unless `labels = tech-cross-platform` |

Adjust `cf[10113]` when auditing a different quarter.

## TPM roster

Lead TPM hygiene applies to epics owned by or associated with these TPMs (use for filtering or grouping reports when the user asks):

Vineet Koul, Deepali Bedi, Anthony VanAlphen, Niraj Jha, Anna Khrustalova, Dan Sondak, Faizan Haq, Piyush Jangam, Sahana Hebbar, Charlene Butler, Divya GopalaKrishnan, Janson Lo, Mick Trenter, Emma Drapp, Mandi Bergeron, Ram Garlapati, Klara Barasevich, Stephanie Dulcey, Mick Trenter.

## Fields to track Jira hygiene through execution

Evaluate every issue returned by the audit JQL against the rules below. An issue **fails** a rule when the FAIL condition matches; otherwise that rule **passes** for that issue.

### Rule 1

**Field name:** Lead TPM

- **FAIL if:** Lead TPM IS EMPTY
- **PASS if:** Lead TPM IS NOT EMPTY

### Rule 2 (P0)

**Field name:** Target Delivery Date

- **FAIL if:** Status IN (`Plan`, `Build`, `Ready to Test`, `Test`, `Ready for Release`) AND Target Delivery Date IS EMPTY
- **PASS if:** Status IN (`Plan`, `Build`, `Ready to Test`, `Test`, `Ready for Release`) AND Target Delivery Date IS NOT EMPTY

(If status is outside that set, Rule 2 does not apply unless Confluence says otherwise.)

### Rule 3

**Field name:** Fix versions

- **FAIL if:** Status IN (`Plan`, `Build`, `Ready to Test`, `Test`, `Ready for Release`) AND Fix Versions IS EMPTY
- **PASS if:** Status IN (`Plan`, `Build`, `Ready to Test`, `Test`, `Ready for Release`) AND Fix Versions IS NOT EMPTY

### Rule 4

**Field name:** Desired Date

- **FAIL if:** Status IN (`Solutioning`, `Plan`, `Build`, `Ready to Test`, `Test`, `Ready for Release`) AND Desired Date < Target Delivery Date
- **PASS if:** Desired Date >= Target Delivery Date

(Both dates must be present to compare; if either is empty, treat as FAIL for Rule 4 when status is in the FAIL status list.)

### Rule 5 (P0)

**Field name:** Status

- **FAIL if:** Status IN (`New`, `Define`) AND Desired Date < 5 weeks from current date
- **PASS if:** Status NOT IN (`New`, `Define`)

Interpret “5 weeks from current date” as: `Desired Date` is strictly before `(today + 5 weeks)` while the epic remains in `New` or `Define`.

### Rule 6 (P0)

**Field name:** Tag = Hard Deadline

- **FAIL if:** Status IN (`New`, `Define`, `Solutioning`, `Build`, `Ready to Test`, `Test`, `Ready for Release`) AND Tag = Hard Deadline AND Desired Date IS EMPTY
- **PASS if:** Status IN (`New`, `Define`, `Solutioning`, `Build`, `Ready to Test`, `Test`, `Ready for Release`) AND Tag = Hard Deadline AND Desired Date IS NOT EMPTY

(If `Hard Deadline` tag is absent, Rule 6 does not apply.)

## Rule priority

**P0:** Rule 2, Rule 5, Rule 6

Flag P0 failures prominently in reports (separate section or column).

## Jira fields to request in API searches

Request at minimum: `key`, `summary`, `status`, `assignee`, `priority`, `issuetype`, `labels`, `fixVersions`, plus API names for:

- Lead TPM
- Target Delivery Date
- Desired Date
- Enabler (dropdown)
- Target Release (multi select)
- `cf[10111]`, `cf[10113]`

Resolve custom field IDs via `GetDynamicTools` / field metadata if name-based fetch fails.
