from git_provider import GitProvider


class GitService:
    def __init__(self, provider: GitProvider):
        self.provider = provider

    def create_repo(self, repo_name):
        return self.provider.create_repository(repo_name)
