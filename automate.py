import os
import time
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DEVIN_API_KEY = os.getenv("DEVIN_API_KEY")
GITHUB_TOKEN = os.getenv("CURRENT_GITHUB_TOKEN")
GITHUB_REPO = os.getenv("CURRENT_GITHUB_REPO")
LOG_FILE = "sessions_log.json"

DEVIN_HEADERS = {
    "Authorization": f"Bearer {DEVIN_API_KEY}",
    "Content-Type": "application/json"
}

GITHUB_HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}


def get_labeled_issues():
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
    params = {"labels": "devin-ready", "state": "open"}
    response = requests.get(url, headers=GITHUB_HEADERS, params=params)
    data = response.json()

    print(f"GitHub API response: {data}")

    if not isinstance(data, list):
        print(f"Error from GitHub API: {data}")
        return []

    return data


def start_devin_session(issue):
    prompt = f"""
    Please fix the following GitHub issue in the repository https://github.com/{GITHUB_REPO}:

    Title: {issue['title']}

    Description:
    {issue['body']}

    Instructions:
    - Make the necessary changes to fix this issue
    - Create a pull request with your changes
    - Keep the changes minimal and focused on the issue
    """

    response = requests.post(
        "https://api.devin.ai/v1/sessions",
        headers=DEVIN_HEADERS,
        json={"prompt": prompt}
    )
    return response.json()


def poll_session(session_id):
    for _ in range(60):  # poll for max 30 minutes
        response = requests.get(
            f"https://api.devin.ai/v1/sessions/{session_id}",
            headers=DEVIN_HEADERS
        )
        data = response.json()
        status = data.get("status")
        print(f"  Session {session_id} status: {status}")

        if status in ["completed", "failed", "stopped"]:
            return data

        time.sleep(30)

    return {"status": "timeout"}


def comment_on_issue(issue_number, session_data):
    status = session_data.get("status")
    url_to_devin = session_data.get("url", "N/A")

    body = f"""
## Devin Automation Update

- **Status:** {status}
- **Devin Session:** {url_to_devin}
- **Completed at:** {datetime.utcnow().isoformat()} UTC

{"✅ Devin has completed work on this issue. Please review the pull request." if status == "completed" else "❌ Devin session did not complete successfully."}
    """

    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues/{issue_number}/comments"
    requests.post(url, headers=GITHUB_HEADERS, json={"body": body})


def remove_label(issue_number):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues/{issue_number}/labels/devin-ready"
    requests.delete(url, headers=GITHUB_HEADERS)
    print(f"  Removed 'devin-ready' label from issue #{issue_number}")


def add_completed_label(issue_number):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues/{issue_number}/labels"
    requests.post(url, headers=GITHUB_HEADERS, json={"labels": ["devin-completed"]})
    print(f"  Added 'devin-completed' label to issue #{issue_number}")


def log_session(issue, session_id, final_status):
    logs = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            logs = json.load(f)

    logs.append({
        "timestamp": datetime.utcnow().isoformat(),
        "issue_number": issue["number"],
        "issue_title": issue["title"],
        "session_id": session_id,
        "status": final_status
    })

    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=2)


def main():
    print("Fetching devin-ready issues...")
    issues = get_labeled_issues()

    if not issues:
        print("No issues found with label 'devin-ready'")
        return

    print(f"Found {len(issues)} issue(s). Starting Devin sessions...")

    for issue in issues:
        print(f"\nProcessing issue #{issue['number']}: {issue['title']}")

        session = start_devin_session(issue)
        session_id = session.get("session_id")

        if not session_id:
            print(f"  Failed to start session: {session}")
            remove_label(issue["number"])
            add_completed_label(issue["number"])
            continue

        print(f"  Session started: {session_id}")
        final_data = poll_session(session_id)
        final_status = final_data.get("status")

        comment_on_issue(issue["number"], final_data)
        log_session(issue, session_id, final_status)
        remove_label(issue["number"])
        add_completed_label(issue["number"])

        print(f"  Done. Status: {final_status}")


if __name__ == "__main__":
    main()