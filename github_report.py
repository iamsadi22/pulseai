import requests
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import os
import json

GITHUB_API_URL = "https://api.github.com"


def fetch_commits(repo: str, since: str, until: Optional[str] = None, token: Optional[str] = None) -> List[dict]:
    """
    Fetch all commits from all branches in a GitHub repo since a given date (and until an optional end date).
    Args:
        repo (str): The GitHub repository in 'owner/repo' format.
        since (str): ISO8601 date string to fetch commits since.
        token (Optional[str]): GitHub personal access token.
        until (Optional[str]): ISO8601 date string to fetch commits until.
    Returns:
        List[dict]: List of unique commit data from all branches.
    """
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    # 1. Get all branches
    branches_url = f"{GITHUB_API_URL}/repos/{repo}/branches"
    branches_resp = requests.get(branches_url, headers=headers)
    if branches_resp.status_code != 200:
        print(f"Failed to fetch branches for {repo}: {branches_resp.status_code}")
        return []
    branches = [b['name'] for b in branches_resp.json()]
    all_commits = {}
    # 2. For each branch, get commits
    for branch in branches:
        page = 1
        while True:
            commits_url = f"{GITHUB_API_URL}/repos/{repo}/commits"
            params = {"sha": branch, "since": since, "per_page": 100, "page": page}
            if until:
                params["until"] = until
            resp = requests.get(commits_url, headers=headers, params=params)
            if resp.status_code != 200:
                break
            commits = resp.json()
            if not commits:
                break
            for commit in commits:
                sha = commit['sha']
                all_commits[sha] = commit  # deduplicate by SHA
            if len(commits) < 100:
                break
            page += 1
    return list(all_commits.values())


def fetch_pull_requests(repo: str, since: str, token: Optional[str] = None) -> List[dict]:
    """
    Fetch PRs from GitHub API since a given date.
    Args:
        repo (str): The GitHub repository in 'owner/repo' format.
        since (str): ISO8601 date string to fetch PRs since.
        token (Optional[str]): GitHub personal access token.
    Returns:
        List[dict]: List of PR data.
    """
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    prs = []
    page = 1
    while True:
        url = f"{GITHUB_API_URL}/repos/{repo}/pulls"
        params = {"state": "all", "sort": "created", "direction": "desc", "per_page": 100, "page": page}
        resp = requests.get(url, headers=headers, params=params)
        if resp.status_code != 200:
            break
        data = resp.json()
        if not data:
            break
        # Filter PRs by created_at >= since
        filtered = [pr for pr in data if pr["created_at"] >= since]
        prs.extend(filtered)
        if len(data) < 100 or not filtered:
            break
        page += 1
    return prs


def group_commits_by_user(commits: List[dict]) -> Dict[str, int]:
    """
    Group commits by GitHub username, falling back to committer if author is missing.
    Args:
        commits (List[dict]): List of commit data.
    Returns:
        Dict[str, int]: Mapping of username to commit count.
    """
    user_commits = defaultdict(int)
    for commit in commits:
        author = commit.get("author")
        committer = commit.get("committer")
        if author and author.get("login"):
            user_commits[author["login"]] += 1
        else:
            if committer and committer.get("login"):
                user_commits[committer["login"]] += 1
            else:
                user_commits["unknown"] += 1
    return dict(user_commits)


def group_prs_by_user(prs: List[dict]) -> Dict[str, dict]:
    """
    Group PRs by GitHub username.
    Args:
        prs (List[dict]): List of PR data.
    Returns:
        Dict[str, dict]: Mapping of username to PR summary (opened, merged).
    """
    user_prs = defaultdict(lambda: {"opened": 0, "merged": 0})
    for pr in prs:
        user = pr["user"]["login"] if pr.get("user") else "unknown"
        user_prs[user]["opened"] += 1
        if pr.get("merged_at"):
            user_prs[user]["merged"] += 1
    return dict(user_prs)


def summarize_prs(prs: List[dict]) -> dict:
    """
    Summarize total PRs opened and merged.
    Args:
        prs (List[dict]): List of PR data.
    Returns:
        dict: Summary with total opened and merged PRs.
    """
    total_opened = len(prs)
    total_merged = sum(1 for pr in prs if pr.get("merged_at"))
    return {"total_opened": total_opened, "total_merged": total_merged}


def fetch_org_repos(org: str, token: Optional[str] = None) -> list:
    """
    Fetch all repositories for a GitHub organization.
    Args:
        org (str): The GitHub organization name.
        token (Optional[str]): GitHub personal access token.
    Returns:
        list: List of repository names in 'owner/repo' format.
    """
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    repos = []
    page = 1
    while True:
        url = f"{GITHUB_API_URL}/orgs/{org}/repos"
        params = {"per_page": 100, "page": page, "type": "all"}
        resp = requests.get(url, headers=headers, params=params)
        if resp.status_code != 200:
            break
        data = resp.json()
        if not data:
            break
        repos.extend([f"{repo['owner']['login']}/{repo['name']}" for repo in data])
        if len(data) < 100:
            break
        page += 1
    return repos 