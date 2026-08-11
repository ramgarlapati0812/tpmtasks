# AGENTS.md

## Cursor Cloud specific instructions

This repo is a small Python CLI toolchain (no server, no database) that turns CSV task
data into normalized JSON and a standalone interactive HTML dashboard for the Promo CTA
project. The only runtime dependency is `pyyaml` (`requirements.txt`); the dependency
refresh is handled by the startup update script, so you normally do not need to install
anything manually.

### Pipeline (two-step, order matters)

`fetch_tasks.py` must run before `generate_dashboard.py` — the generator reads the JSON
that fetch writes. Standard commands are in the [README](README.md) and
[`.cursor/skills/tpm-dashboard/SKILL.md`](.cursor/skills/tpm-dashboard/SKILL.md):

- Multi-platform (default): `python3 scripts/fetch_tasks.py --pretty` then
  `python3 scripts/generate_dashboard.py`
- Android single-platform variant (non-obvious: uses its own input/layout/output paths):

```bash
python3 scripts/fetch_tasks.py \
  --input data/android_promo_cta_tasks.csv \
  --milestones data/android_milestones.csv \
  --layout config/dashboard-layout-android.yaml \
  --output data/android-dashboard.json --pretty
python3 scripts/generate_dashboard.py \
  --input data/android-dashboard.json \
  --output canvas/android-promo-cta-dashboard.html
```

### Gotchas

- The generated JSON (`data/dashboard.json`, `data/android-dashboard.json`) is
  gitignored; the HTML in `canvas/` is committed. Regenerate JSON before generating HTML
  after a fresh clone, since the JSON will not exist yet.
- There is no test suite or configured linter. For a lightweight "lint"/sanity check use
  `python3 -m py_compile scripts/fetch_tasks.py scripts/generate_dashboard.py`.
- Jira mode (`--source jira`) requires `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`
  (see [`.env.example`](.env.example)); without them it raises. CSV mode is the default
  and needs no secrets.
- To preview a generated dashboard headlessly (Chrome is available in the VM):
  `google-chrome-stable --headless --no-sandbox --disable-gpu --window-size=1280,1800 --screenshot=out.png "file:///workspace/canvas/android-promo-cta-dashboard.html"`
  (the dbus connection errors it prints are harmless).
