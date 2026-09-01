#!/usr/bin/env python3
"""Refresh the stats line in README.md between the STATS markers.

Stdlib only, REST only — runs fine with the default GITHUB_TOKEN (no GraphQL,
no PAT). Exits non-zero without touching the README if any API call fails, so
the workflow never commits stale or broken numbers.
"""

import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://api.github.com"
OWNER = os.environ.get("GITHUB_OWNER", "TimFang4162")
README = Path(__file__).resolve().parents[2] / "README.md"

STATS_RE = re.compile(r"(<!-- STATS:START.*?-->\n)(.*?)(\n<!-- STATS:END)", re.DOTALL)


def api(path: str):
    req = urllib.request.Request(API + path, headers=auth_headers())
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def commit_count(repo: str) -> int:
    # Commit search API returns wildly unstable totals, so count commits on the
    # default branch via pagination (per_page=1, last page number = count).
    req = urllib.request.Request(
        f"{API}/repos/{OWNER}/{repo}/commits?per_page=1", headers=auth_headers())
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.load(resp)
        link = resp.headers.get("Link", "")
    last = re.search(r'page=(\d+)>; rel="last"', link)
    return int(last.group(1)) if last else len(body)


def auth_headers() -> dict:
    return {
        "User-Agent": OWNER + "-stats-action",
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + os.environ["GITHUB_TOKEN"],
    }


def search_count(query: str) -> int:
    return api("/search/issues?q=" + urllib.parse.quote(query))["total_count"]


def fmt(n: int) -> str:
    return f"{n:,}"


def main() -> int:
    user = api("/users/" + OWNER)
    repos = [r for r in api(f"/users/{OWNER}/repos?per_page=100") if not r["fork"]]
    stars = sum(r["stargazers_count"] for r in repos)
    commits = sum(commit_count(r["name"]) for r in repos)
    prs = search_count(f"author:{OWNER} type:pr")
    followers = user["followers"]

    line = (f"⭐ {fmt(stars)} stars · 🕓 {fmt(commits)} commits · "
            f"🔀 {fmt(prs)} PRs · 👥 {fmt(followers)} followers")

    text = README.read_text(encoding="utf-8")
    if not STATS_RE.search(text):
        print("ERROR: STATS markers not found in README.md", file=sys.stderr)
        return 1
    README.write_text(STATS_RE.sub(lambda m: m.group(1) + line + m.group(3), text),
                      encoding="utf-8")
    print("stats line set to:", line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
