# Promo Cta Project Dashboard — Reference Structure

This document captures the inferred layout from the shared canvas
[Promo Cta Project Dashboard](https://cursor.com/dashboard/shared-canvases?shareId=canvas-2F1oi-qm-uZnHt4gkDHFcXW8).
The original canvas content is not programmatically accessible; this structure follows
the plan's TPM promo/CTA dashboard conventions and is used as the implementation baseline.

## Header

- Project title: **Promo CTA Project Dashboard**
- Last refreshed timestamp
- Milestone countdown (days to next key date)

## Summary Stats (rollup + per platform)

| Stat | Description |
|------|-------------|
| Total tasks | Count of all tracked work items |
| Complete | Tasks in Done/Closed status |
| In progress | Tasks actively being worked |
| Blocked | Tasks with blocker flag or Blocked status |
| % complete | Complete / Total × 100 |
| Days to milestone | Days until next milestone date |

## Platform Sections

Each platform (Apple, Android, Lightbeam, Roku) gets:

1. **Platform summary row** — same stats as rollup, scoped to platform
2. **Task table** — sortable list of work items
3. **Platform-specific fields** — shown only when relevant

### Shared task columns

| Column | Description |
|--------|-------------|
| ID | Task identifier (Jira key or internal ID) |
| Title | Task summary |
| Owner | Assignee |
| Status | To Do / In Progress / In Review / Done / Blocked |
| Priority | Highest / High / Medium / Low |
| Target date | Due or target completion date |
| Blocker | Yes/No or blocker description |
| Epic | Parent epic or feature name |

### Platform-specific columns

| Platform | Extra fields |
|----------|--------------|
| Apple | Store status, build target (iOS/tvOS/macOS), TestFlight status |
| Android | Play track, build version, device certification |
| Lightbeam | Release channel, deployment environment |
| Roku | Channel certification, SDK version, build type |

## Milestone Timeline

Key dates displayed chronologically:

- Code freeze
- QA sign-off
- Store/channel submission
- Release / launch

## Risks and Blockers

Filtered view of tasks where `blocker = yes` or status = Blocked, grouped by platform.

## Recent Activity

Status changes in the last 7 days (task ID, title, old status → new status, date).
