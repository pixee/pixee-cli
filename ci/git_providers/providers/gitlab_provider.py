"""
This module provides classes and interfaces for interacting with Gitlab.
"""
import base64
from git_provider import GitProvider, PullRequestData, BranchData
import gitlab


class GitLabProvider(GitProvider):
    def __init__(self, project_id, private_token, gitlab_url="https://gitlab.com"):
        self.client = gitlab.Gitlab(gitlab_url, private_token=private_token)
        self.project = self.client.projects.get(project_id, lazy=True)

    def create_branch(self, branch_name, source_branch):
        gitlab_branch_data = self.project.branches.create(
            {"branch": branch_name, "ref": source_branch}
        )

        return BranchData(
            name=gitlab_branch_data.name,
            last_commit_id=gitlab_branch_data.commit["id"],
            last_commit_author=gitlab_branch_data.commit["author_name"],
            web_url=gitlab_branch_data.web_url,
        )

    def create_commit(self, file_path, branch, content, commit_message):
        file = self.project.files.get(file_path, ref=branch)
        file.content = content
        file.save(branch=branch, commit_message=commit_message)

    def get_pr(self, pr_id):
        # TODO normalize the return value between providers
        pr_data = self.project.mergerequests.get(pr_id)
        return PullRequestData(
            id=pr_data["iid"],
            title=pr_data["title"],
            creator=pr_data["author"]["username"],
            web_url=pr_data.web_url,
        )

    def get_file(self, file_path, branch_name):
        file = self.project.files.get(file_path, ref=branch_name)
        content = base64.b64decode(file.content).decode("UTF-8")
        return content

    def create_pr(self, source_branch, target_branch, title, description):
        pr_data = self.project.mergerequests.create(
            {
                "source_branch": source_branch,
                "target_branch": target_branch,
                "title": title,
                "description": description,
            }
        )
        return PullRequestData(
            id=pr_data.iid,
            title=pr_data.title,
            creator=pr_data.author["username"],
            web_url=pr_data.web_url,
        )

    def create_pr_comment(self, pr_id, comment):
        merge_request = self.project.mergerequests.get(pr_id)

        merge_request.notes.create({"body": comment})
