#!/usr/bin/env python3
"""Fetch a GitHub user's public footprint into one JSON file for CV generation.

Usage:
    python fetch_github.py <username-or-profile-url> [--out cv-output/<user>/github.json]
                           [--token TOKEN] [--deep N] [--readme-chars N] [--include-forks]

Auth (optional but recommended — 5,000 req/h instead of 60, plus pinned repos and
contribution stats): pass --token, or set GITHUB_TOKEN / GH_TOKEN, or be logged in
with the GitHub CLI (`gh auth login`). The token never leaves this machine except
to api.github.com, and it is never written to the output file.

Standard library only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import days_ago, eprint, save_json  # noqa: E402

API = "https://api.github.com"
USER_AGENT = "github-to-cv (+https://github.com/topics/github-to-cv)"

GRAPHQL_QUERY = """
query($login: String!) {
  user(login: $login) {
    pinnedItems(first: 6, types: REPOSITORY) {
      nodes { ... on Repository { nameWithOwner } }
    }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
      totalIssueContributions
      contributionCalendar { totalContributions }
    }
    repositoriesContributedTo(first: 50, contributionTypes: [COMMIT, PULL_REQUEST],
                              includeUserRepositories: false,
                              orderBy: {field: STARGAZERS, direction: DESC}) {
      nodes { nameWithOwner url description stargazerCount primaryLanguage { name } }
    }
  }
}
"""


class RateLimited(RuntimeError):
    pass


class GitHub:
    def __init__(self, token=None, verbose=True):
        self.token = token
        self.verbose = verbose
        self.calls = 0
        self.remaining = None
        self.reset = None

    # -- transport ---------------------------------------------------------
    def _request(self, url, accept="application/vnd.github+json", payload=None):
        headers = {"Accept": accept, "User-Agent": USER_AGENT, "X-GitHub-Api-Version": "2022-11-28"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    self.calls += 1
                    self._track(resp.headers)
                    return resp.status, resp.read()
            except urllib.error.HTTPError as err:
                self.calls += 1
                self._track(err.headers)
                body = err.read()
                if err.code in (403, 429) and (self.remaining == 0 or b"rate limit" in body.lower()):
                    raise RateLimited(self._rate_message()) from None
                if err.code in (502, 503, 504) and attempt < 2:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                return err.code, body
            except urllib.error.URLError as err:
                if attempt < 2:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                raise RuntimeError(f"Network error talking to GitHub: {err.reason}") from None
        return 599, b""

    def _track(self, headers):
        if not headers:
            return
        rem = headers.get("X-RateLimit-Remaining")
        rst = headers.get("X-RateLimit-Reset")
        if rem is not None:
            try:
                self.remaining = int(rem)
            except ValueError:
                pass
        if rst is not None:
            try:
                self.reset = int(rst)
            except ValueError:
                pass

    def _rate_message(self):
        when = ""
        if self.reset:
            when = " Resets at " + datetime.fromtimestamp(self.reset, tz=timezone.utc).strftime("%H:%M UTC") + "."
        return ("GitHub API rate limit reached." + when +
                " Unauthenticated requests are limited to 60/hour. Set GITHUB_TOKEN (a fine-grained token with "
                "public read access is enough) or run `gh auth login`, then re-run.")

    # -- helpers -----------------------------------------------------------
    def get_json(self, path, params=None):
        url = path if path.startswith("http") else API + path
        if params:
            url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
        status, body = self._request(url)
        if status == 404:
            return None
        if status >= 400:
            raise RuntimeError(f"GitHub API error {status} for {url}: {body[:300].decode('utf-8', 'replace')}")
        return json.loads(body.decode("utf-8")) if body else None

    def get_raw(self, path):
        status, body = self._request(API + path, accept="application/vnd.github.raw+json")
        if status >= 400:
            return None
        return body.decode("utf-8", "replace")

    def paginate(self, path, params=None, max_pages=5):
        params = dict(params or {})
        params.setdefault("per_page", 100)
        out = []
        for page in range(1, max_pages + 1):
            params["page"] = page
            batch = self.get_json(path, params) or []
            out.extend(batch)
            if len(batch) < params["per_page"]:
                break
        return out

    def graphql(self, query, variables):
        if not self.token:
            return None
        status, body = self._request(API + "/graphql", payload={"query": query, "variables": variables})
        if status >= 400:
            return None
        data = json.loads(body.decode("utf-8"))
        if data.get("errors"):
            eprint("  (GraphQL returned errors; continuing without it:", data["errors"][0].get("message"), ")")
        return data.get("data")


# ----------------------------------------------------------------------------

def discover_token(cli_token=None):
    if cli_token:
        return cli_token, "--token"
    for var in ("GITHUB_TOKEN", "GH_TOKEN"):
        if os.environ.get(var):
            return os.environ[var], var
    if shutil.which("gh"):
        try:
            res = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=10)
            tok = res.stdout.strip()
            if res.returncode == 0 and tok:
                return tok, "gh auth token"
        except (OSError, subprocess.SubprocessError):
            pass
    return None, None


def parse_login(value: str) -> str:
    v = value.strip().rstrip("/")
    m = re.match(r"^(?:https?://)?(?:www\.)?github\.com/([A-Za-z0-9-]+)", v, re.I)
    if m:
        return m.group(1)
    v = v.lstrip("@")
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}", v):
        raise SystemExit(f"'{value}' does not look like a GitHub username or profile URL.")
    return v


REPO_KEEP = ["name", "full_name", "html_url", "description", "homepage", "language", "topics",
             "stargazers_count", "forks_count", "watchers_count", "open_issues_count", "size",
             "created_at", "updated_at", "pushed_at", "fork", "archived", "is_template", "has_pages",
             "default_branch"]


def trim_repo(r):
    out = {k: r.get(k) for k in REPO_KEEP}
    lic = r.get("license") or {}
    out["license"] = lic.get("spdx_id") if isinstance(lic, dict) else None
    out["topics"] = r.get("topics") or []
    return out


def prelim_rank(r):
    """Cheap ranking used only to decide which repos get a deep fetch."""
    score = (r.get("stargazers_count") or 0) * 3 + (r.get("forks_count") or 0) * 2
    age = days_ago(r.get("pushed_at"))
    if age is not None:
        score += 25 if age < 180 else 12 if age < 365 else 4 if age < 730 else 0
    if r.get("description"):
        score += 6
    if r.get("topics"):
        score += 4
    if r.get("homepage"):
        score += 4
    score += min((r.get("size") or 0) / 500, 6)
    if r.get("archived"):
        score -= 5
    return score


def fetch(login, token=None, deep=None, readme_chars=8000, include_forks=False, verbose=True):
    gh = GitHub(token=token, verbose=verbose)
    deep = deep if deep is not None else (30 if token else 12)
    log = (lambda *a: eprint(*a)) if verbose else (lambda *a: None)
    warnings = []

    log(f"→ Fetching profile for @{login} ({'authenticated' if token else 'unauthenticated: 60 req/h limit'})")
    user = gh.get_json(f"/users/{login}")
    if not user:
        raise SystemExit(f"GitHub user '{login}' not found.")
    login = user.get("login", login)

    result = {
        "schema": "github-to-cv/github@1",
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "authenticated": bool(token),
        "profile": {k: user.get(k) for k in ["login", "name", "bio", "company", "blog", "location", "email",
                                            "twitter_username", "hireable", "public_repos", "public_gists",
                                            "followers", "following", "created_at", "updated_at", "html_url",
                                            "avatar_url", "type"]},
        "social_accounts": [],
        "orgs": [],
        "profile_readme": None,
        "pinned": [],
        "repos": [],
        "external_contributions": [],
        "contributions_last_year": None,
        "warnings": warnings,
    }

    def guarded(label, fn, default=None):
        try:
            return fn()
        except RateLimited:
            raise
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"{label}: {exc}")
            return default

    try:
        result["social_accounts"] = guarded("social accounts", lambda: gh.get_json(f"/users/{login}/social_accounts"), []) or []
        orgs = guarded("orgs", lambda: gh.get_json(f"/users/{login}/orgs"), []) or []
        result["orgs"] = [{"login": o.get("login"), "description": o.get("description")} for o in orgs]

        log("→ Listing repositories")
        repos = gh.paginate(f"/users/{login}/repos", {"type": "owner", "sort": "pushed"}, max_pages=5)
        own = [r for r in repos if not r.get("fork")]
        forks = [r for r in repos if r.get("fork")]

        readme = guarded("profile README", lambda: gh.get_raw(f"/repos/{login}/{login}/readme"))
        if readme:
            result["profile_readme"] = readme[:readme_chars]

        # GraphQL extras (token only)
        gql = guarded("graphql", lambda: gh.graphql(GRAPHQL_QUERY, {"login": login})) if token else None
        pinned_names = []
        if gql and gql.get("user"):
            u = gql["user"]
            pinned_names = [n["nameWithOwner"] for n in (u.get("pinnedItems") or {}).get("nodes", []) if n]
            cc = u.get("contributionsCollection") or {}
            result["contributions_last_year"] = {
                "total": (cc.get("contributionCalendar") or {}).get("totalContributions"),
                "commits": cc.get("totalCommitContributions"),
                "pull_requests": cc.get("totalPullRequestContributions"),
                "reviews": cc.get("totalPullRequestReviewContributions"),
                "issues": cc.get("totalIssueContributions"),
            }
            result["repositories_contributed_to"] = [
                {"full_name": n["nameWithOwner"], "url": n["url"], "description": n.get("description"),
                 "stars": n.get("stargazerCount"), "language": (n.get("primaryLanguage") or {}).get("name")}
                for n in (u.get("repositoriesContributedTo") or {}).get("nodes", []) if n]
        result["pinned"] = pinned_names

        # Deep-fetch the most promising repos (+ every pinned repo).
        candidates = sorted(own + (forks if include_forks else []), key=prelim_rank, reverse=True)
        pinned_set = {p.lower() for p in pinned_names}
        deep_set = {r["full_name"].lower() for r in candidates[:deep]} | pinned_set
        log(f"→ Reading languages + README for {len([r for r in candidates if r['full_name'].lower() in deep_set])} repos")
        for r in own + forks:
            item = trim_repo(r)
            item["pinned"] = r["full_name"].lower() in pinned_set
            if r["full_name"].lower() in deep_set and (include_forks or not r.get("fork")):
                full = r["full_name"]
                item["languages"] = guarded(f"languages {full}", lambda: gh.get_json(f"/repos/{full}/languages"), {}) or {}
                text = guarded(f"readme {full}", lambda: gh.get_raw(f"/repos/{full}/readme"))
                item["readme"] = (text or "")[:readme_chars]
                item["readme_length"] = len(text or "")
                item["deep"] = True
            else:
                item["deep"] = False
            result["repos"].append(item)

        # Merged PRs to repositories the user does not own.
        log("→ Searching merged pull requests to other projects")
        q = f"author:{login} type:pr is:merged -user:{login}"
        search = guarded("PR search", lambda: gh.get_json("/search/issues", {"q": q, "per_page": 100, "sort": "updated"}), {}) or {}
        by_repo = {}
        for it in search.get("items", []):
            full = (it.get("repository_url") or "").split("/repos/")[-1]
            if not full:
                continue
            g = by_repo.setdefault(full, {"full_name": full, "url": f"https://github.com/{full}", "merged_prs": 0,
                                          "titles": [], "pr_urls": [], "first": None, "last": None})
            g["merged_prs"] += 1
            if len(g["titles"]) < 6:
                g["titles"].append(it.get("title"))
                g["pr_urls"].append(it.get("html_url"))
            when = (it.get("pull_request") or {}).get("merged_at") or it.get("closed_at")
            if when:
                g["first"] = min(filter(None, [g["first"], when]))
                g["last"] = max(filter(None, [g["last"], when]))
        result["external_prs_total"] = search.get("total_count", 0)
        org_logins = {o["login"].lower() for o in result["orgs"] if o.get("login")}
        groups = sorted(by_repo.values(), key=lambda g: -g["merged_prs"])
        for g in groups[:10]:
            meta = guarded(f"repo {g['full_name']}", lambda: gh.get_json(f"/repos/{g['full_name']}"))
            if meta:
                g.update({"stars": meta.get("stargazers_count"), "description": meta.get("description"),
                          "language": meta.get("language"), "topics": meta.get("topics") or []})
            g["owner_is_user_org"] = g["full_name"].split("/")[0].lower() in org_logins
        result["external_contributions"] = groups

    except RateLimited as exc:
        warnings.append(str(exc))
        result["partial"] = True
        eprint("!", exc)

    result["api_calls"] = gh.calls
    result["rate_limit_remaining"] = gh.remaining
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("user", help="GitHub username or profile URL")
    ap.add_argument("--out", help="Output path (default: cv-output/<user>/github.json)")
    ap.add_argument("--token", help="GitHub token (else GITHUB_TOKEN / GH_TOKEN / gh CLI)")
    ap.add_argument("--no-token", action="store_true", help="Do not look for a token")
    ap.add_argument("--deep", type=int, help="How many repos to read READMEs/languages for (default 12, or 30 with a token)")
    ap.add_argument("--readme-chars", type=int, default=8000)
    ap.add_argument("--include-forks", action="store_true", help="Deep-fetch forks too")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    login = parse_login(args.user)
    token, source = (None, None) if args.no_token else discover_token(args.token)
    if source and not args.quiet:
        eprint(f"→ Using GitHub token from {source}")

    try:
        data = fetch(login, token=token, deep=args.deep, readme_chars=args.readme_chars,
                     include_forks=args.include_forks, verbose=not args.quiet)
    except RateLimited as exc:
        eprint(f"✗ {exc}")
        return 2
    except RuntimeError as exc:
        eprint(f"✗ {exc}")
        eprint("  If you're in a sandbox or behind a proxy that blocks api.github.com, run this script on your own "
               "machine and share the resulting github.json, or paste your top repos' descriptions and READMEs.")
        return 1
    out = Path(args.out) if args.out else Path("cv-output") / data["profile"]["login"] / "github.json"
    save_json(data, out)

    p = data["profile"]
    own = [r for r in data["repos"] if not r["fork"]]
    stars = sum(r.get("stargazers_count") or 0 for r in own)
    print(f"✓ Saved {out}")
    print(f"  {p.get('name') or p['login']} — {len(own)} own repos, {stars} stars, "
          f"{len(data['external_contributions'])} external projects with merged PRs, {data['api_calls']} API calls")
    if data["warnings"]:
        print(f"  {len(data['warnings'])} warning(s): " + "; ".join(data["warnings"][:3]))
    if data.get("partial"):
        print("  ! Partial data (rate limited). Add a token and re-run for complete results.")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
