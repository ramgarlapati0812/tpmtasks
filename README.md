# tpmtasks

Multi-platform TPM dashboard for the **Promo CTA Project**, covering **Apple**, **Android**, **Lightbeam**, and **Roku**.

Modeled on the shared canvas [Promo Cta Project Dashboard](https://cursor.com/dashboard/shared-canvases?shareId=canvas-2F1oi-qm-uZnHt4gkDHFcXW8).

## Quick start

```bash
pip install -r requirements.txt
python scripts/fetch_tasks.py --pretty
python scripts/generate_dashboard.py
```

Open [`canvas/promo-cta-dashboard.html`](canvas/promo-cta-dashboard.html) in a browser for a standalone preview.

**Shareable link (works now):**

https://htmlpreview.github.io/?https://raw.githubusercontent.com/ramgarlapati0812/tpmtasks/main/canvas/promo-cta-dashboard.html

**Production link (after enabling GitHub Pages):** https://ramgarlapati0812.github.io/tpmtasks/

Enable Pages at [repo settings → Pages](https://github.com/ramgarlapati0812/tpmtasks/settings/pages) with source **GitHub Actions**, then re-run the deploy workflow.

## Regenerate in Cursor

Ask the agent:

> Generate the Promo CTA TPM dashboard for Apple, Android, Lightbeam, and Roku

Or invoke the skill at [`.cursor/skills/tpm-dashboard/SKILL.md`](.cursor/skills/tpm-dashboard/SKILL.md).

To publish for the team, click **Publish** in the canvas toolbar after generation. See [`docs/publishing.md`](docs/publishing.md) for the full workflow.

## Repository layout

```
config/                  Platform and layout definitions
data/                    CSV inputs and generated dashboard.json
docs/                    Reference dashboard structure
scripts/                 fetch_tasks.py, generate_dashboard.py
canvas/                  Generated HTML dashboard
.cursor/skills/          Cursor canvas skill for repeatable generation
```

## Data sources

### CSV (default MVP)

1. Export tasks to CSV with a `platform` column (`apple`, `android`, `lightbeam`, `roku`)
2. Replace or point to your file:
   ```bash
   python scripts/fetch_tasks.py --input path/to/tasks.csv --pretty
   ```
3. Column aliases are defined in [`config/field-mapping.yaml`](config/field-mapping.yaml)

Sample data: [`data/sample_tasks.csv`](data/sample_tasks.csv)

### Jira (optional)

Copy [`.env.example`](.env.example) to `.env` and set:

- `JIRA_BASE_URL`
- `JIRA_EMAIL`
- `JIRA_API_TOKEN`
- `JIRA_JQL` (optional)

```bash
python scripts/fetch_tasks.py --source jira --pretty
```

Tasks are mapped to platforms via Jira **components** (Apple, Android, Lightbeam, Roku).

## Platforms

| Platform | ID | Notes |
|----------|----|-------|
| Apple | `apple` | iOS, tvOS, macOS — store/TestFlight fields |
| Android | `android` | Android, AndroidTV — Play track/version fields |
| Lightbeam | `lightbeam` | Internal release channel / deployment env |
| Roku | `roku` | Channel certification, SDK version, build type |

Definitions: [`config/platforms.yaml`](config/platforms.yaml)

## Milestones

Edit [`data/milestones.csv`](data/milestones.csv):

```csv
name,date,platform
Code freeze,2026-08-18,all
Release,2026-08-28,all
```

## Reference

Dashboard section spec: [`docs/reference-structure.md`](docs/reference-structure.md)

Layout config: [`config/dashboard-layout.yaml`](config/dashboard-layout.yaml)
