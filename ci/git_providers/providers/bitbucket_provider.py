"""
This module provides classes and interfaces for interacting with Bitbucket.
"""
from git_provider import GitProvider, PullRequestData, BranchData
from git_providers.lib.bb_client import BitbucketClient


class BitbucketProvider(GitProvider):
    def __init__(
        self,
        workspace,
        repository,
        private_token,
        bitbucket_url="https://bitbucket.org",
    ):
        self.client = BitbucketClient(
            workspace, repository, private_token, bitbucket_url
        )
        self.bitbucket_url = bitbucket_url

    def create_branch(self, branch_name: str, source_branch: str):
        branch = self.client.create_branch(branch_name, source_branch)
        return BranchData(
            name=branch["name"],
            last_commit_id=branch["target"]["hash"],
            last_commit_author="",
            web_url=f"{self.bitbucket_url}/{self.client.workspace}/{self.client.repository}/branches/{branch_name}",
        )

    def create_commit(
        self, file_path: str, branch: str, content: str, commit_message: str
    ):
        return self.client.commit_file(file_path, branch, commit_message, content)

    def get_pr(self, pr_id):
        pull_request = self.client.get_pull_request_info(pr_id)
        return PullRequestData(
            id=pull_request["id"],
            title=pull_request["title"],
            creator=pull_request["author"]["display_name"],
            web_url=pull_request["links"]["html"]["href"],
        )

    def get_file(self, file_path: str, branch_name: str):
        return self.client.read_file(file_path, branch_name).decode("UTF-8")

    def create_pr(
        self, source_branch: str, target_branch: str, title: str, description: str
    ):
        pull_request = self.client.create_pull_request(
            title, description, source_branch, target_branch
        )
        return PullRequestData(
            id=pull_request["id"],
            title=pull_request["title"],
            creator=pull_request["author"]["display_name"],
            web_url=pull_request["links"]["html"]["href"],
        )

    def create_pr_comment(self, pr_id, comment: str):
        return self.client.add_comment_to_pull_request(pr_id, comment)
