import requests


class BitbucketClient:
    def __init__(
        self,
        workspace,
        repository,
        api_token,
        base_url="https://api.bitbucket.org/2.0/",
    ):
        self.headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {api_token}",
        }
        self.base_url = base_url
        self.workspace = workspace
        self.repository = repository

    def _make_request(self, method, url, data=None, **kwargs):
        """Generic method to make HTTP requests"""
        full_url = f"{self.base_url}{url}"
        response = requests.request(
            method, full_url, json=data, headers=self.headers, timeout=10, **kwargs
        )
        if response.ok:
            # Check the content type of the response
            if "application/json" in response.headers.get("Content-Type", ""):
                return response.json()
            else:
                return response.content
        else:
            # You can improve this with more detailed error handling
            response.raise_for_status()

    def get_repo_info(self):
        """Get information about a specific repository"""
        return self._make_request(
            "GET", f"repositories/{self.workspace}/{self.repository}"
        )

    def create_branch(self, new_branch_name, source_branch):
        """Create a new branch in a repository"""
        source_branch_hash = self.get_branch_hash(source_branch)
        if not source_branch_hash:
            raise ValueError(
                f"Could not find hash for branch '{source_branch}' in '{self.repository}'"
            )
        data = {"name": new_branch_name, "target": {"hash": source_branch_hash}}
        return self._make_request(
            "POST",
            f"repositories/{self.workspace}/{self.repository}/refs/branches",
            data,
        )

    def get_branch_hash(self, branch_name):
        """Helper function to get the hash of a branch"""
        return self._make_request(
            "GET",
            f"repositories/{self.workspace}/{self.repository}/refs/branches/{branch_name}",
        )["target"]["hash"]

    def read_file(self, file_path, branch):
        """Read the content of a file from a specified branch in a repository"""
        url = (
            f"repositories/{self.workspace}/{self.repository}/src/{branch}/{file_path}"
        )
        response = self._make_request("GET", url)
        # The response should contain the file content
        return response if response else None

    def commit_file(self, file_path, branch, commit_message, content):
        """Commit a file to a specified repository and branch"""
        if isinstance(content, str):
            content = content.encode("utf-8")
        # Prepare the data as multipart/form-data
        data = {"branch": branch, "message": commit_message}
        files = {file_path: content}
        url = f"repositories/{self.workspace}/{self.repository}/src"
        full_url = f"{self.base_url}{url}"
        response = requests.post(
            full_url, data=data, files=files, headers=self.headers, timeout=10
        )
        return response.text

    def commit_files(self, files_data, branch, commit_message):
        """
        Commit multiple files to a specified repository and branch.

        :param files_data: Dictionary where keys are file paths and values are file contents.
        :param branch: Branch name to commit the files.
        :param commit_message: Commit message.
        :return: Response text from the API call.
        """
        # Encode file contents to bytes if they are strings
        encoded_files_data = {
            file_path: (
                content.encode("utf-8") if isinstance(content, str) else content
            )
            for file_path, content in files_data.items()
        }

        # Prepare the data as multipart/form-data
        data = {"branch": branch, "message": commit_message}
        url = f"repositories/{self.workspace}/{self.repository}/src"
        full_url = f"{self.base_url}{url}"

        response = requests.post(
            full_url,
            data=data,
            files=encoded_files_data,
            headers=self.headers,
            timeout=10,
        )

        return response.text

    def create_pull_request(
        self,
        title,
        description,
        source_branch,
        destination_branch,
    ):
        """Create a pull request in a specified repository"""
        url = f"repositories/{self.workspace}/{self.repository}/pullrequests"
        data = {
            "title": title,
            "source": {"branch": {"name": source_branch}},
            "destination": {"branch": {"name": destination_branch}},
            "description": description,
            "close_source_branch": False,
            "reviewers": [],
        }
        return self._make_request("POST", url, data)

    def get_pull_request_info(self, pull_request_id):
        """Retrieve information about a specific pull request"""
        url = f"repositories/{self.workspace}/{self.repository}/pullrequests/{pull_request_id}"
        return self._make_request("GET", url)

    def add_comment_to_pull_request(self, pull_request_id, comment):
        """Add a Markdown formatted comment to a pull request"""
        url = f"repositories/{self.workspace}/{self.repository}/pullrequests/{pull_request_id}/comments"
        data = {
            "content": {
                "raw": comment  # The comment is expected to be in Markdown format
            }
        }
        return self._make_request("POST", url, data)
