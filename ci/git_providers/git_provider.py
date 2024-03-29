"""
This module provides classes and interfaces for interacting with Git repositories.

It includes data classes to represent pull request and branch data, and defines an abstract base class `GitProvider`. The `GitProvider` class serves as a template for implementing Git-related operations such as branch creation, commit creation, file retrieval, pull request handling, and adding comments to pull requests. Specific Git provider implementations can inherit from this abstract base class to ensure consistent interfaces across different Git services.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing_extensions import Self


@dataclass
class PullRequestData:
    """
    A data class representing the data of a pull request.

    Attributes:
        id (int): The unique identifier of the pull request.
        title (str): The title of the pull request.
        creator (str): The username of the person who created the pull request.
        web_url (str): The URL to view the pull request on the web.
    """

    id: int
    title: str
    creator: str
    web_url: str


@dataclass
class BranchData:
    """
    A data class representing the data of a Git branch.

    Attributes:
        name (str): The name of the branch.
        last_commit_id (str): The identifier of the last commit on the branch.
        last_commit_author (str): The username of the author of the last commit.
        web_url (str): The URL to view the branch on the web.
    """

    name: str
    last_commit_id: str
    last_commit_author: str
    web_url: str


class GitProvider(ABC):
    """
    Abstract base class representing a generic Git provider.

    This class provides an interface for various Git-related operations.
    """

    @classmethod
    def create_client(cls, provider) -> Self:
        """
        Create an instance of a GitProvider client.

        Args:
            provider: The provider-specific client class to instantiate.

        Returns:
            An instance of the specified GitProvider client.
        """
        return provider

    @abstractmethod
    def create_branch(self, branch_name: str, source_branch: str):
        """
        Abstract method to create a new branch.

        Args:
            branch_name (str): The name of the new branch to create.
            source_branch (str): The name of the source branch to branch off.
        """
        pass

    @abstractmethod
    def create_commit(
        self, file_path: str, branch: str, content: str, commit_message: str
    ):
        """
        Abstract method to create a new commit.

        Args:
            file_path (str): The path of the file to commit.
            branch (str): The name of the branch to commit to.
            content (str): The content to be committed.
            commit_message (str): The commit message.
        """
        pass

    @abstractmethod
    def get_file(self, file_path: str, branch_name: str):
        """
        Abstract method to retrieve a file from a branch.

        Args:
            file_path (str): The path of the file to retrieve.
            branch_name (str): The name of the branch where the file is located.
        """
        pass

    @abstractmethod
    def get_pr(self, pr_id: str):
        """
        Abstract method to retrieve a pull request.

        Args:
            pr_id (str): The identifier of the pull request to retrieve.
        """
        pass

    @abstractmethod
    def create_pr(
        self, source_branch: str, target_branch: str, title: str, description: str
    ):
        """
        Abstract method to create a new pull request.

        Args:
            source_branch (str): The name of the source branch.
            target_branch (str): The name of the target branch.
            title (str): The title of the pull request.
            description (str): The description of the pull request.
        """
        pass

    @abstractmethod
    def create_pr_comment(self, pr_id, comment: str):
        """
        Abstract method to create a comment on a pull request.

        Args:
            pr_id: The identifier of the pull request to comment on.
            comment (str): The content of the comment.
        """
        pass
