from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse

import httpx

GITHUB_ISSUE_URL = re.compile(
    r"^https?://(?:www\.)?github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/issues/(?P<number>\d+)/?$",
    re.IGNORECASE,
)
GITHUB_SHORT_REF = re.compile(
    r"^(?P<owner>[^/#\s]+)/(?P<repo>[^/#\s]+)(?:#(?P<number>\d+)|/(?P<number2>\d+))?$"
)


class GitHubFetchError(Exception):
    pass


@dataclass(frozen=True)
class GitHubIssueRef:
    owner: str
    repo: str
    number: int

    @property
    def source_url(self) -> str:
        return f"https://github.com/{self.owner}/{self.repo}/issues/{self.number}"

    @property
    def api_url(self) -> str:
        return f"https://api.github.com/repos/{self.owner}/{self.repo}/issues/{self.number}"


@dataclass(frozen=True)
class GitHubIssueContent:
    title: str
    body: str
    source_url: str


class GitHubClient(Protocol):
    def fetch_issue(self, ref: GitHubIssueRef) -> GitHubIssueContent: ...


def parse_github_ref(raw: str) -> GitHubIssueRef:
    value = raw.strip()
    if not value:
        raise GitHubFetchError("GitHub reference is empty")

    url_match = GITHUB_ISSUE_URL.match(value)
    if url_match:
        return GitHubIssueRef(
            owner=url_match.group("owner"),
            repo=url_match.group("repo"),
            number=int(url_match.group("number")),
        )

    if value.startswith("http://") or value.startswith("https://"):
        parsed = urlparse(value)
        if "github.com" in parsed.netloc:
            raise GitHubFetchError(
                "Could not parse GitHub issue URL; use https://github.com/owner/repo/issues/N"
            )
        raise GitHubFetchError("Only GitHub issue URLs are supported")

    short_match = GITHUB_SHORT_REF.match(value)
    if short_match:
        number = short_match.group("number") or short_match.group("number2")
        return GitHubIssueRef(
            owner=short_match.group("owner"),
            repo=short_match.group("repo"),
            number=int(number),
        )

    raise GitHubFetchError(
        "Invalid GitHub reference; use a URL or owner/repo#number (e.g. elastic/kibana#12345)"
    )


class HttpxGitHubClient:
    def __init__(self, *, client: httpx.Client | None = None, token: str | None = None) -> None:
        headers = {"Accept": "application/vnd.github+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = client or httpx.Client(timeout=15.0, headers=headers)

    def fetch_issue(self, ref: GitHubIssueRef) -> GitHubIssueContent:
        try:
            response = self._client.get(ref.api_url)
        except httpx.RequestError as exc:
            raise GitHubFetchError(f"Failed to reach GitHub: {exc}") from exc

        if response.status_code == 404:
            raise GitHubFetchError(
                f"Issue not found: {ref.owner}/{ref.repo}#{ref.number}"
            )
        if response.status_code >= 400:
            raise GitHubFetchError(
                f"GitHub API error ({response.status_code}) for {ref.source_url}"
            )

        payload = response.json()
        if payload.get("pull_request"):
            raise GitHubFetchError(
                f"{ref.source_url} is a pull request, not an issue"
            )

        title = (payload.get("title") or "").strip()
        body = (payload.get("body") or "").strip()
        if not title:
            raise GitHubFetchError(f"GitHub issue has no title: {ref.source_url}")

        return GitHubIssueContent(title=title, body=body, source_url=ref.source_url)
