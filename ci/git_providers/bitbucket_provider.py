from git_provider import GitProvider


class BitbucketProvider(GitProvider):
    def __init__(self, credentials):
        self.credentials = credentials

    def get_repository(self, repo_name):
        # Implementation for Bitbucket
        pass

    def create_repository(self, repo_name):
        # Implementation for Bitbucket
        pass
