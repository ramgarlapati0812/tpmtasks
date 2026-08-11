# Publishing the Dashboard

The repo generates dashboard data and a standalone HTML preview. You can share the dashboard in two ways:

## Shareable web link (GitHub Pages)

### Works now (no setup required)

https://htmlpreview.github.io/?https://raw.githubusercontent.com/ramgarlapati0812/tpmtasks/main/canvas/promo-cta-dashboard.html

This renders the latest dashboard HTML from the `main` branch. Share this link with your team immediately.

### Production URL (recommended)

**Live URL:** https://ramgarlapati0812.github.io/tpmtasks/

One-time setup (repo owner):

1. Open [tpmtasks → Settings → Pages](https://github.com/ramgarlapati0812/tpmtasks/settings/pages)
2. Set **Source** to **GitHub Actions**
3. Re-run the **Deploy dashboard to GitHub Pages** workflow from the Actions tab

After that, every push to `main` auto-deploys the dashboard.

1. Merge your changes to `main`
2. GitHub Actions rebuilds and redeploys (or run **Deploy dashboard to GitHub Pages** manually from the Actions tab)

To update data before deploy locally:

```bash
python3 scripts/fetch_tasks.py --pretty
python3 scripts/generate_dashboard.py
git add canvas/promo-cta-dashboard.html data/sample_tasks.csv
git commit -m "Refresh dashboard data"
git push
```

---

## Cursor shared canvas

To create a **Cursor shared canvas** (like the reference Promo Cta Project Dashboard), follow these steps in Cursor Desktop.

## 1. Refresh data

```bash
pip install -r requirements.txt
python3 scripts/fetch_tasks.py --pretty
```

Replace `data/sample_tasks.csv` with your real export, or use Jira:

```bash
python3 scripts/fetch_tasks.py --source jira --pretty
```

## 2. Generate the canvas in Cursor Agent

Open Cursor Agent and run:

> Generate the Promo CTA TPM dashboard for Apple, Android, Lightbeam, and Roku using the tpm-dashboard skill

The skill at [`.cursor/skills/tpm-dashboard/SKILL.md`](../.cursor/skills/tpm-dashboard/SKILL.md) instructs the agent to:

1. Run `scripts/fetch_tasks.py`
2. Read `data/dashboard.json`
3. Render an interactive canvas with platform tabs, stats, milestones, blockers, and recent activity

## 3. Iterate

If layout or data looks wrong:

- Adjust `config/dashboard-layout.yaml` or `config/platforms.yaml`
- Re-run `python3 scripts/fetch_tasks.py --pretty`
- Ask the agent to regenerate the canvas

For a quick HTML preview without the canvas:

```bash
python3 scripts/generate_dashboard.py
open canvas/promo-cta-dashboard.html
```

## 4. Publish shared canvas

Once the canvas renders correctly:

1. Open the canvas in Cursor
2. Click **Publish** in the canvas toolbar
3. Copy the shared URL for your team

Requirements:

- Pro, Teams, or Enterprise plan
- Team-enabled account
- Non-legacy privacy mode (Legacy Privacy Mode blocks publishing)

Team admins can manage shared canvases at
[Cursor Dashboard → Settings → Shared Canvases](https://cursor.com/dashboard/settings#shared-canvases).

## 5. Keep data current

| Frequency | Action |
|-----------|--------|
| Daily | Re-run `fetch_tasks.py` and ask agent to refresh canvas |
| On export | Drop new CSV into `data/` and re-run scripts |
| Automated | Schedule Jira fetch via CI or cron with env secrets |
