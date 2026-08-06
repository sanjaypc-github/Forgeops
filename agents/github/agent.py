from typing import Dict, Any
from memory.state import InvestigationState, GithubFindings
from tools.github.tool import GitHubTool

class GitHubAgent:
    """
    GitHub Agent
    Queries repository changes to investigate code commits and merges related to the incident.
    """
    def __init__(self, tool: GitHubTool = None):
        self.tool = tool or GitHubTool()

    def run(self, state: InvestigationState) -> Dict[str, Any]:
        print("[GitHub Agent] Analyzing code repository...")
        
        # Collect recent commits and PRs
        commits = self.tool.get_recent_commits(limit=5)
        prs = self.tool.get_pull_requests(state="closed", limit=3)
        
        # Consolidate changed files
        changed_files = set()
        author = None
        timestamp = None
        
        if commits:
            author = commits[0].get("author")
            timestamp = commits[0].get("date")
            for commit in commits:
                for file in commit.get("files_changed", []):
                    changed_files.add(file)
                    
        github_findings: GithubFindings = {
            "recent_commits": commits,
            "recent_prs": prs,
            "changed_files": list(changed_files),
            "author": author,
            "timestamp": timestamp,
            "error": None
        }

        logs = state.get("logs_trace", [])
        logs.append(f"GitHub Agent successfully fetched {len(commits)} commits and {len(prs)} PRs.")

        return {
            "github": github_findings,
            "logs_trace": logs
        }
