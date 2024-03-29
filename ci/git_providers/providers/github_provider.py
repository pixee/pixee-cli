"""
This module provides classes and interfaces for interacting with Github.
"""
import base64
from github import Github
from git_provider import GitProvider, PullRequestData, BranchData


class GitHubProvider(GitProvider):
    def __init__(
        self, repo_name, personal_access_token, github_url="https://api.github.com"
    ):
        self.client = Github(base_url=github_url, login_or_token=personal_access_token)
        self.repo = self.client.get_repo(repo_name)
        self.base_url = self.repo.html_url

    def create_branch(self, branch_name, source_branch):
        source_branch_ref = self.repo.get_git_ref(f"heads/{source_branch}")
        self.repo.create_git_ref(
            f"refs/heads/{branch_name}", source_branch_ref.object.sha
        )

        # Fetch the new branch details
        new_branch_ref = self.repo.get_git_ref(f"heads/{branch_name}")

        return BranchData(
            name=branch_name,
            last_commit_id=new_branch_ref.object.sha,
            # Additional details like author can be fetched with an extra API call if needed
            last_commit_author=None,
            web_url=f"{self.base_url}/tree/{branch_name}",
        )

    def create_commit(self, file_path, branch, content, commit_message):
        file = self.repo.get_contents(file_path, ref=branch)
        self.repo.update_file(
            file.path, commit_message, content, file.sha, branch=branch
        )

    def get_pr(self, pr_id):
        pr = self.repo.get_pull(pr_id)
        return PullRequestData(
            id=pr.number, title=pr.title, creator=pr.user.login, web_url=pr.html_url
        )

    def get_file(self, file_path, branch_name):
        file = self.repo.get_contents(file_path, ref=branch_name)
        content = base64.b64decode(file.content).decode("UTF-8")
        return content

    def create_pr(self, source_branch, target_branch, title, description):
        pr = self.repo.create_pull(
            title=title, body=description, base=target_branch, head=source_branch
        )

        return PullRequestData(
            id=pr.number, title=pr.title, creator=pr.user.login, web_url=pr.html_url
        )

    def create_pr_comment(self, pr_id, comment):
        pr = self.repo.get_pull(pr_id)
        pr.create_issue_comment(body=comment)
