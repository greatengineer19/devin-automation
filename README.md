# Devin Auto-Remediation

An event-driven automation that uses the [Devin API](https://docs.devin.ai/api-reference/overview) to autonomously remediate security vulnerabilities in [Apache Superset](https://github.com/greatengineer19/forked_superset).

When a GitHub issue is labeled **`devin-ready`**, this system automatically spins up a Devin session, instructs it to fix the issue, and posts the result (PR link + status) back as an issue comment — zero human intervention required after label assignment.

---

## How It Works

```
GitHub Issue labeled "devin-ready"
        ↓
GitHub Actions workflow triggers (event-driven)
        ↓
Docker container builds and runs automate.py
        ↓
Devin API → new session created with issue context as prompt
        ↓
Poll every 30s until Devin completes or fails (max 30 min)
        ↓
Post comment on GitHub issue (PR link + session URL + status)
        ↓
Swap label: devin-ready → devin-completed
        ↓
Log session to sessions_log.json (observability)
```

---

## Repository Structure

```
devin-automation/
├── automate.py                        # Core automation script
├── scan_issues.py                     # Vulnerability scanner (creates issues automatically)
├── Dockerfile                         # Packages the automation
├── requirements.txt                   # Python dependencies
├── sessions_log.json                  # Observability log (appended after each run)
├── index.html                         # Live dashboard (GitHub Pages)
└── .github/
    └── workflows/
        └── devin-trigger.yml          # GitHub Actions: label trigger + nightly scan
```

---

## Prerequisites

| Requirement | Where to get it |
|---|---|
| Devin API key | [app.devin.ai](https://app.devin.ai) → Settings → API Keys |
| GitHub Personal Access Token | [github.com/settings/tokens](https://github.com/settings/tokens) (scope: `repo`) |
| Docker | [docs.docker.com/get-docker](https://docs.docker.com/get-docker/) |
| Fork of Apache Superset | [greatengineer19/forked_superset](https://github.com/greatengineer19/forked_superset) |

---

## Quickstart (Local)

### 1. Clone this repo

```bash
git clone https://github.com/greatengineer19/devin-automation
cd devin-automation
```

### 2. Set up environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in:

```env
DEVIN_API_KEY=your_devin_api_key
CURRENT_GITHUB_TOKEN=your_github_token
CURRENT_GITHUB_REPO=greatengineer19/forked_superset
```

### 3. Build and run with Docker

```bash
docker build -t devin-automation .
docker run --rm \
  --env-file .env \
  -v $(pwd)/sessions_log.json:/app/sessions_log.json \
  devin-automation python automate.py
```

The script will:
- Fetch all open issues labeled `devin-ready` from the Superset fork
- Start a Devin session per issue
- Poll until completion
- Post a comment and update labels automatically

---

## Triggering via GitHub Actions

This is the primary production path. No local setup required.

### Automatic (Event-Driven)

1. Go to your Superset fork: [greatengineer19/forked_superset/issues](https://github.com/greatengineer19/forked_superset/issues)
2. Open any issue
3. Apply the **`devin-ready`** label
4. GitHub Actions fires automatically → Devin gets to work

### Manual Trigger (for testing)

1. Go to [Actions tab](https://github.com/greatengineer19/devin-automation/actions)
2. Select **Devin Auto-Remediation**
3. Click **Run workflow**

### Nightly Vulnerability Scan

A cron job runs every night at midnight UTC:
- Runs `scan_issues.py` inside Docker
- Uses `pip-audit` to detect CVEs in the Superset fork's `requirements/base.txt`
- Automatically creates GitHub issues labeled `devin-pending` for any new findings
- An engineer reviews and relabels to `devin-ready` to approve remediation

---

## GitHub Actions Setup

Add these three secrets to this repo at:
**Settings → Secrets and variables → Actions → New repository secret**

| Secret Name | Value |
|---|---|
| `DEVIN_API_KEY` | Your Devin API key |
| `CURRENT_GITHUB_TOKEN` | Your GitHub PAT (scope: `repo`) |
| `CURRENT_GITHUB_REPO` | `greatengineer19/forked_superset` |

---

## Issue Labels Used

Create these labels in the **Superset fork** repo:

| Label | Color | Meaning |
|---|---|---|
| `devin-ready` | 🔵 Blue `#0075ca` | Issue is approved — Devin will pick it up |
| `devin-completed` | 🟢 Green `#0e8a16` | Devin has finished and opened a PR |

---

## Observability

### Live Dashboard

Hosted at: **[greatengineer19.github.io/devin-automation](https://greatengineer19.github.io/devin-automation)**

Reads live data directly from the GitHub API and shows:
- Total issues remediated vs. pending
- Success / failure signals per session
- Pull requests opened by Devin
- Recent workflow run history
- Throughput over time

### Session Log

`sessions_log.json` is appended after each run:

```json
[
  {
    "timestamp": "2026-05-19T14:10:00",
    "issue_number": 3,
    "issue_title": "chore(deps): upgrade flask from 2.3.3 to 3.1.3",
    "session_id": "ses_abc123",
    "status": "completed"
  }
]
```

This answers the engineering leader's question: **"How do I know this is working?"**

---

## Issues Remediated

The following security vulnerabilities were identified and remediated in [greatengineer19/forked_superset](https://github.com/greatengineer19/forked_superset):

| Issue | Package | CVE | Status |
|---|---|---|---|
| [#1 – Upgrade Flask 2.3.3 → 3.1.3](https://github.com/greatengineer19/forked_superset/issues/1) | `flask` | CVE-2026-27205 | ✅ PR opened by Devin |
| [#2 – Upgrade NumPy 1.26.4 → 2.x](https://github.com/greatengineer19/forked_superset/issues/2) | `numpy` | — | ✅ PR opened by Devin |
| [#3 – Upgrade Pandas 2.2.3 → 2.3.x](https://github.com/greatengineer19/forked_superset/issues/3) | `pandas` | — | 🔵 In progress |
| [#4 – Upgrade Flask-SQLAlchemy](https://github.com/greatengineer19/forked_superset/issues/4) | `flask-sqlalchemy` | — | 🔵 In progress |
| [#5 – Upgrade cryptography package](https://github.com/greatengineer19/forked_superset/issues/5) | `cryptography` | — | 🔵 In progress |

---

## Architecture Decision Notes

**Why GitHub Actions as the trigger?**
GitHub Actions is natively event-driven, free, and requires zero infrastructure. The label event is a clean, human-controlled gate — engineers decide what goes to Devin, nothing runs without intent.

**Why Docker?**
Ensures the automation runs identically in CI and locally. Any engineer can clone this repo and reproduce the exact same run with one command.

**Why poll instead of webhook from Devin?**
The Devin API currently returns session status via polling. The 30-second interval keeps CI costs low while staying responsive. Max wait is 30 minutes — sufficient for dependency upgrades.

**Production extension points:**
- Replace GitHub issue trigger with a Jira webhook (same architecture, different integration point)
- Add Slack notification on session completion
- Parallelize sessions with Python threads for bulk remediation
- Integrate `pip-audit` nightly scan into a full SIEM pipeline

---

## Related Repositories

| Repo | Purpose |
|---|---|
| [greatengineer19/devin-automation](https://github.com/greatengineer19/devin-automation) | This repo — the automation engine |
| [greatengineer19/forked_superset](https://github.com/greatengineer19/forked_superset) | Apache Superset fork — where issues and PRs live |