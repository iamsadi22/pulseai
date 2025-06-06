from datetime import datetime, timedelta, timezone
from typing import Dict, Any
import json
from transformers import pipeline

def get_date_range(days: int) -> (str, str):
    """
    Get ISO8601 date strings for the start and end of the range.
    Args:
        days (int): Number of days in the range.
    Returns:
        (str, str): (start_date, end_date) in ISO8601 format.
    """
    end = datetime.utcnow()
    start = end - timedelta(days=days)
    return start.strftime('%Y-%m-%dT%H:%M:%SZ'), end.strftime('%Y-%m-%dT%H:%M:%SZ')


def format_markdown_report(start_date: str, end_date: str, commit_summary: Dict[str, int], pr_summary: Dict[str, Any], prs_by_user: Dict[str, Any]) -> str:
    """
    Format the engineering pulse report as Markdown.
    Args:
        start_date (str): Start date of the report.
        end_date (str): End date of the report.
        commit_summary (Dict[str, int]): Commits per user.
        pr_summary (Dict[str, Any]): Total PRs opened/merged.
        prs_by_user (Dict[str, Any]): PRs by user.
    Returns:
        str: Markdown formatted report.
    """
    md = f"# Engineering Pulse Report ({start_date[:10]} to {end_date[:10]})\n\n"
    md += "## 🧑‍💻 Commit Activity\n"
    md += "| Developer        | Commits |\n|------------------|---------|\n"
    for user, count in sorted(commit_summary.items(), key=lambda x: -x[1]):
        md += f"| @{user:<16} | {count:<7} |\n"
    md += "\n## 🔀 Pull Request Summary\n"
    md += f"- **Total PRs Opened:** {pr_summary['total_opened']}\n"
    md += f"- **Total PRs Merged:** {pr_summary['total_merged']}\n\n"
    md += "### 📌 PRs by Developer\n"
    for user, stats in prs_by_user.items():
        md += f"- @{user}: {stats['opened']} opened, {stats['merged']} merged\n"
    md += "\n## 🚩 Potential Blockers or Issues Detected\n"
    for user, count in commit_summary.items():
        if count == 0:
            md += f"- @{user} had no commits this period.\n"
    for pr in prs_by_user.values():
        if pr.get('state') == 'open':
            created_at = pr.get('created_at')
            if created_at:
                created_dt = datetime.strptime(created_at, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
                days_open = (datetime.now(timezone.utc) - created_dt).days
                if days_open > 3:
                    md += f"- **[pulseai/web]** [PR #{pr['number']}: {pr.get('title', 'Untitled')}](https://github.com/pulseai/web/pull/{pr['number']}) by @{pr['user']['login']} has been open for **{days_open} days**.\n"
    return md


def format_json_report(start_date: str, end_date: str, commit_summary: Dict[str, int], pr_summary: Dict[str, Any], prs_by_user: Dict[str, Any]) -> str:
    """
    Format the engineering pulse report as JSON.
    Args:
        start_date (str): Start date of the report.
        end_date (str): End date of the report.
        commit_summary (Dict[str, int]): Commits per user.
        pr_summary (Dict[str, Any]): Total PRs opened/merged.
        prs_by_user (Dict[str, Any]): PRs by user.
    Returns:
        str: JSON formatted report.
    """
    report = {
        "date_range": {"start": start_date, "end": end_date},
        "commits": commit_summary,
        "pull_requests": {
            "summary": pr_summary,
            "by_user": prs_by_user
        }
    }
    return json.dumps(report, indent=2)


def detect_anomalies(commit_summary, prs, days_range=7):
    """
    Detect anomalies and flag patterns in developer and PR activity.
    Args:
        commit_summary (dict): Commits per user.
        prs (list): List of PR dicts.
        days_range (int): Days in the reporting period.
    Returns:
        list: List of alert strings.
    """
    alerts = []
    # Flag developers with no commits
    for user, count in commit_summary.items():
        if count == 0:
            alerts.append(f"@{user} had no commits this period.")
    # Flag PRs open > 3 days
    now = datetime.now(timezone.utc)
    for pr in prs:
        if pr.get('state') == 'open':
            created_at = pr.get('created_at')
            if created_at:
                created_dt = datetime.strptime(created_at, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
                days_open = (now - created_dt).days
                if days_open > 3:
                    alerts.append(f"PR #{pr.get('number')} by @{pr['user']['login']} has been open for {days_open} days.")
    return alerts


def assess_goal_status(commit_summary, pr_summary, alerts):
    """
    Assess if engineering throughput is healthy and spot blockers, based on stats and alerts.
    Args:
        commit_summary (dict): Commits per user.
        pr_summary (dict): PR summary (opened/merged).
        alerts (list): List of alert strings.
    Returns:
        str: Goal assessment statement.
    """
    if not commit_summary:
        return "No commit activity detected. Engineering throughput is low."
    all_active = all(count > 0 for count in commit_summary.values())
    merge_ratio = pr_summary['total_merged'] / pr_summary['total_opened'] if pr_summary['total_opened'] else 0
    if all_active and merge_ratio > 0.7 and not alerts:
        return "Throughput is healthy. Most developers contributed and PRs were merged quickly."
    if alerts:
        return "Potential blockers or issues detected: " + " ".join(alerts)
    if not all_active:
        return "Some developers had no commits. Throughput may be lower than usual."
    if merge_ratio < 0.5:
        return "Warning: Less than half of PRs were merged. There may be review or merge bottlenecks."
    return "Throughput is lower than usual. Consider checking for blockers or dependencies."


def assess_goal_status_hf(commit_summary, pr_summary, alerts, model_name="mistralai/Mistral-7B-Instruct-v0.2"):
    """
    Use a Hugging Face model to assess engineering throughput and blockers.
    Args:
        commit_summary (dict): Commits per user.
        pr_summary (dict): PR summary (opened/merged).
        alerts (list): List of alert strings.
        model_name (str): Hugging Face model name (default: google/flan-t5-base)
    Returns:
        str: AI-generated goal assessment statement.
    Example usage:
        commit_summary = {'@kabir-coderex': 126, '@nasimcoderex': 82}
        pr_summary = {'total_opened': 32, 'total_merged': 27}
        alerts = ["PR #1250 by @nasimcoderex has been open for 6 days."]
        assessment = assess_goal_status_hf(commit_summary, pr_summary, alerts)
        print(assessment)
    """
    prompt = (
        "You are an engineering manager assistant. Given the following data, "
        "write a concise, insightful assessment of the team's throughput and any potential blockers.\n\n"
        f"Commit summary (commits per user): {commit_summary}\n"
        f"PR summary: {pr_summary}\n"
        f"Alerts: {alerts}\n\n"
        "Assessment:"
    )
    generator = pipeline("text2text-generation", model=model_name)
    result = generator(prompt, max_new_tokens=80, do_sample=True, temperature=0.7)
    return result[0]['generated_text'].strip() 