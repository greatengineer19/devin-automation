import os
import json
import subprocess
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("CURRENT_GITHUB_TOKEN")
GITHUB_REPO = os.getenv("CURRENT_GITHUB_REPO")

GITHUB_HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}


def run_pip_audit():
    print("Running pip-audit to find vulnerabilities...")
    try:
        result = subprocess.run(
            ["pip-audit", "--format", "json", "-r", "requirements/base.txt"],
            capture_output=True, text=True
        )
        return json.loads(result.stdout)
    except Exception as e:
        print(f"pip-audit failed: {e}")
        return []


def get_existing_issue_titles():
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
    params = {"state": "open", "per_page": 100}
    response = requests.get(url, headers=GITHUB_HEADERS, params=params)
    issues = response.json()
    if not isinstance(issues, list):
        return []
    return [issue["title"] for issue in issues]


def create_issue(title, body):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
    payload = {
        "title": title,
        "body": body,
        "labels": ["devin-pending"]
    }
    response = requests.post(url, headers=GITHUB_HEADERS, json=payload)
    data = response.json()
    print(f"  Created issue #{data.get('number')}: {title}")
    return data


def main():
    print(f"Starting vulnerability scan at {datetime.utcnow().isoformat()} UTC")

    existing_titles = get_existing_issue_titles()
    audit_results = run_pip_audit()

    if not audit_results:
        print("No vulnerabilities found or pip-audit failed.")
        return

    created = 0
    for dep in audit_results:
        name = dep.get("name")
        version = dep.get("version")
        vulns = dep.get("vulns", [])

        for vuln in vulns:
            vuln_id = vuln.get("id")
            description = vuln.get("description", "No description available.")
            fix_versions = vuln.get("fix_versions", [])
            fix = fix_versions[0] if fix_versions else "latest"

            title = f"chore(deps): upgrade {name} from {version} (#{vuln_id})"

            if title in existing_titles:
                print(f"  Skipping duplicate: {title}")
                continue

            body = f"""## Vulnerability Found: {vuln_id}

**Package:** `{name}=={version}`
**Fix version:** `{fix}`

### Description
{description}

### Action Required
Upgrade `{name}` from `{version}` to `{fix}` in the requirements files.

---
*This issue was automatically created by the vulnerability scanner.*
*An engineer must review and apply the `devin-approved` label to trigger Devin.*
"""
            create_issue(title, body)
            created += 1

    print(f"\nScan complete. {created} new issue(s) created with 'devin-pending' label.")


if __name__ == "__main__":
    main()