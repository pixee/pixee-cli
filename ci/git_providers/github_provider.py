from git_provider import GitProvider


class GitHubProvider(GitProvider):
    def __init__(self, credentials):
        self.credentials = credentials

    def get_repository(self, repo_name):
        # Implementation for GitHub
        pass

    def create_repository(self, repo_name):
        # Implementation for GitHub
        pass
