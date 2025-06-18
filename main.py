import argparse
import os
from dotenv import load_dotenv
from github_report import fetch_commits, fetch_pull_requests, group_commits_by_user, group_prs_by_user, summarize_prs, fetch_org_repos
from utils import get_date_range, format_markdown_report, format_json_report, detect_anomalies, assess_goal_status, assess_goal_status_hf
import datetime

import requests

def send_slack_notification(summary, report_path):
    if os.getenv("SEND_SLACK_NOTIF", "false").lower() != "true":
        return

    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("Slack webhook not configured.")
        return

    message = {
        "text": f"*Engineering Pulse Report*\n{summary}\nReport saved at `{report_path}`"
    }

    response = requests.post(webhook_url, json=message)
    if response.status_code != 200:
        print(f"Slack notification failed: {response.text}")


def load_config():
    """
    Load configuration from .env and CLI arguments.
    Returns:
        dict: Configuration dictionary.
    """
    load_dotenv()
    parser = argparse.ArgumentParser(description="Generate GitHub Engineering Pulse Report.")
    parser.add_argument('--repo', type=str, help='GitHub repo in owner/repo format')
    parser.add_argument('--org', type=str, help='GitHub organization name (for all repos)')
    parser.add_argument('--days', type=int, help='Days range for the report')
    parser.add_argument('--output', type=str, choices=['md', 'json'], default='md', help='Output format')
    parser.add_argument('--file', type=str, help='Output file path (optional)')
    args = parser.parse_args()

    config = {
        'GITHUB_TOKEN': os.getenv('GITHUB_TOKEN'),
        'GITHUB_REPO': args.repo or os.getenv('GITHUB_REPO'),
        'GITHUB_ORG': args.org or os.getenv('GITHUB_ORG'),
        'DAYS_RANGE': int(args.days) if args.days else int(os.getenv('DAYS_RANGE', 7)),
        'OUTPUT_FORMAT': args.output,
        'OUTPUT_FILE': args.file
    }
    return config


def main():
    """
    Main entry point for generating the engineering pulse report.
    """
    config = load_config()
    start_date, end_date = get_date_range(config['DAYS_RANGE'])
    all_commits = []
    all_prs = []
    repos = []
    # If both --repo and --org are provided, only use --repo (repo takes precedence)
    if config.get('GITHUB_REPO'):
        repos = [config['GITHUB_REPO']]
    elif config.get('GITHUB_ORG'):
        print(f"Fetching all repos for organization {config['GITHUB_ORG']}...")
        repos = fetch_org_repos(config['GITHUB_ORG'], config['GITHUB_TOKEN'])
        print(f"Found {len(repos)} repos. Fetching data for each...")
    else:
        print('Error: GitHub repo or org must be specified via --repo/--org or GITHUB_REPO/GITHUB_ORG in .env')
        return
    for repo in repos:
        print(f"Fetching data for {repo} from {start_date[:10]} to {end_date[:10]}...")
        all_commits.extend(fetch_commits(repo, start_date, end_date, config['GITHUB_TOKEN']))
        all_prs.extend(fetch_pull_requests(repo, start_date, config['GITHUB_TOKEN']))
    commit_summary = group_commits_by_user(all_commits)
    prs_by_user = group_prs_by_user(all_prs)
    pr_summary = summarize_prs(all_prs)

    # Heuristic Anomaly Detection
    alerts = detect_anomalies(commit_summary, all_prs, days_range=config['DAYS_RANGE'])
    # Goal Assessment
    goal_statement = assess_goal_status_hf(commit_summary, pr_summary, alerts)

    if config['OUTPUT_FORMAT'] == 'json':
        import json
        report = format_json_report(start_date, end_date, commit_summary, pr_summary, prs_by_user)
        report_dict = json.loads(report)
        report_dict['alerts'] = alerts
        report_dict['goal_assessment'] = goal_statement
        report = json.dumps(report_dict, indent=2)
        ext = 'json'
    else:
        report = format_markdown_report(start_date, end_date, commit_summary, pr_summary, prs_by_user)
        if alerts:
            report += "\n## 🚩 Alerts\n" + "\n".join(f"- {a}" for a in alerts) + "\n"
        report += f"\n## 🎯 Goal Assessment\n{goal_statement}\n"
        ext = 'md'

    # Always save to reports/report-YYYY-MM-DD.ext unless --file is specified
    if config['OUTPUT_FILE']:
        output_path = config['OUTPUT_FILE']
    else:
        today = datetime.date.today().isoformat()
        output_path = f"reports/report-{today}.{ext}"
    with open(output_path, 'w') as f:
        f.write(report)
    print(f"Report saved to {output_path}")
    send_slack_notification(summary_text, report_path)
    if not config['OUTPUT_FILE']:
        print(report)


if __name__ == "__main__":
    main() 