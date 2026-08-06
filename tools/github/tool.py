import os
from typing import List, Dict, Any, Optional

class GitHubTool:
    """
    Tool to query GitHub REST API for code changes, commits, and PRs.
    """
    def __init__(self, token: Optional[str] = None, repository: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.repository = repository or os.getenv("GITHUB_REPOSITORY")
        
    def get_recent_commits(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Fetches the recent commits from the repository.
        """
        if not self.token or not self.repository:
            # Return Mock Data for local testing / sandbox fallback
            return [
                {
                    "sha": "a1b2c3d4e5f6g7h8",
                    "author": "sanjay-developer",
                    "date": "2026-08-06T14:30:00Z",
                    "message": "feat(checkout): add redis cache layer to checkout api",
                    "files_changed": ["services/checkout/main.go", "services/checkout/cache.go"]
                },
                {
                    "sha": "9z8y7x6w5v4u3t2s",
                    "author": "dev-team-lead",
                    "date": "2026-08-05T09:15:00Z",
                    "message": "fix(db): update postgres connection pool configuration",
                    "files_changed": ["config/database.yml"]
                }
            ]
        
        # Real implementation using Github API (requests or httpx)
        # TODO: Implement REST requests to https://api.github.com/repos/{repository}/commits
        return []

    def get_pull_requests(self, state: str = "closed", limit: int = 5) -> List[Dict[str, Any]]:
        """
        Fetches recent pull requests.
        """
        if not self.token or not self.repository:
            return [
                {
                    "id": 1024,
                    "title": "feat(checkout): add redis cache layer to checkout api",
                    "author": "sanjay-developer",
                    "merged_at": "2026-08-06T14:45:00Z",
                    "url": "https://github.com/example/repo/pull/1024"
                }
            ]
        return []

    def get_file_content(self, file_path: str, ref: Optional[str] = None) -> str:
        """
        Gets contents of a file at a specific Git reference.
        """
        if not self.token or not self.repository:
            return "# Mock content for " + file_path
        return ""
