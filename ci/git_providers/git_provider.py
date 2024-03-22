from abc import ABC, abstractmethod


class GitProvider(ABC):
    @abstractmethod
    def create_branch(self, branch_name, source_branch):
        pass

    @abstractmethod
    def create_commit(self, file_path, branch, content, commit_message):
        pass

    @abstractmethod
    def get_file(self, file_path, branch_name):
        pass

    @abstractmethod
    def get_pr(self, pr_id):
        pass

    @abstractmethod
    def create_pr(self, source_branch, target_branch, title, description):
        pass

    @abstractmethod
    def create_pr_comment(self, pr_id, comment):
        pass
