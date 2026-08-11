---
name: tpm-dashboard
description: Generate the Promo CTA multi-platform TPM dashboard for Apple, Android, Lightbeam, and Roku. Use when the user asks for a TPM dashboard, promo CTA status, platform task tracker, or shared canvas refresh.
---

# TPM Multi-Platform Dashboard Skill

Generate an interactive Cursor canvas dashboard for the **Promo CTA Project** across four platforms:
**Apple**, **Android**, **Lightbeam**, and **Roku**.

## When to use

Trigger this skill when the user asks to:

- Generate or refresh the Promo CTA dashboard
- Show TPM task status by platform
- Build a shared canvas for Apple / Android / Lightbeam / Roku
- Update milestone, blocker, or release tracking views

## Workflow

1. **Refresh data**
   ```bash
   pip install -r requirements.txt
   python scripts/fetch_tasks.py --source csv --input data/sample_tasks.csv --pretty
   ```
   Or, with Jira credentials in `.env`:
   ```bash
   python scripts/fetch_tasks.py --source jira --pretty
   ```

2. **Read config**
   - Layout: [`config/dashboard-layout.yaml`](../../config/dashboard-layout.yaml)
   - Platforms: [`config/platforms.yaml`](../../config/platforms.yaml)
   - Reference structure: [`docs/reference-structure.md`](../../docs/reference-structure.md)

3. **Load output**
   - Read `data/dashboard.json` for normalized task data grouped by platform.

4. **Build the canvas**
   Create an interactive canvas with these sections (in order):

   | Section | Content |
   |---------|---------|
   | Header | Title, subtitle, last refreshed, days to milestone |
   | Overall summary | Stat cards: total, complete, in progress, blocked, % complete, days to milestone |
   | Platform tabs | One tab each for Apple, Android, Lightbeam, Roku |
   | Per-platform panel | Platform stat row + task table with shared columns and platform-specific extras |
   | Milestone timeline | Chronological list from `milestones` |
   | Risks & blockers | Filtered table of blocked tasks |
   | Recent activity | Status updates from last 7 days |

5. **Formatting rules**
   - Status badge colors from `dashboard-layout.yaml` → `status_colors`
   - Sort tasks by priority (Highest first), then target date ascending
   - Dates: `YYYY-MM-DD`
   - Show platform-specific columns only on that platform's tab:
     - **Apple**: store_status, build_target, testflight_status
     - **Android**: play_track, build_version, device_certification
     - **Lightbeam**: release_channel, deployment_environment
     - **Roku**: channel_certification, sdk_version, build_type

6. **Optional HTML artifact**
   For a standalone preview outside the canvas:
   ```bash
   python scripts/generate_dashboard.py
   ```
   Opens [`canvas/promo-cta-dashboard.html`](../../canvas/promo-cta-dashboard.html).

7. **Publish shared canvas**
   After the canvas renders correctly in Cursor:
   - Click **Publish** in the canvas toolbar
   - Share the URL with the team (requires Pro/Teams plan, non-legacy privacy mode)

## Data sources

| Source | Command | Notes |
|--------|---------|-------|
| CSV (MVP) | `--source csv --input data/sample_tasks.csv` | Replace with your export; see `config/field-mapping.yaml` |
| Jira | `--source jira` | Set `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, optional `JIRA_JQL` |

**Lightbeam** is treated as its own platform with Jira component / CSV value `lightbeam`.
Map tasks using the `platform` column or Jira component name.

## Customization

- Add real tasks: replace `data/sample_tasks.csv` or point `--input` to your export
- Adjust milestones: edit `data/milestones.csv`
- Change layout/stats: edit `config/dashboard-layout.yaml`
- Add platforms or fields: edit `config/platforms.yaml` and `config/field-mapping.yaml`

## Canvas layout reference

Use the stat card + tabbed table pattern from the reference canvas
[Promo Cta Project Dashboard](https://cursor.com/dashboard/shared-canvases?shareId=canvas-2F1oi-qm-uZnHt4gkDHFcXW8).
Full section spec: [`docs/reference-structure.md`](../../docs/reference-structure.md).

## Quality checks

Before publishing:

- [ ] All four platform tabs render with tasks
- [ ] Rollup stats match sum of platform tasks
- [ ] Blockers section lists PROMO tasks with `blocker=yes` or Blocked status
- [ ] Milestone countdown uses the nearest upcoming milestone date
- [ ] Platform-specific columns appear only on the correct tab
