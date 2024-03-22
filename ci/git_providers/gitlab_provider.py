from git_provider import GitProvider
import gitlab
import base64


class GitLabProvider(GitProvider):
    def __init__(self, project_id, private_token, gitlab_url="https://gitlab.com"):
        self.client = gitlab.Gitlab(gitlab_url, private_token=private_token)
        self.project = self.client.projects.get(project_id, lazy=True)

    def create_branch(self, branch_name, source_branch):
        return self.project.branches.create(
            {"branch": branch_name, "ref": source_branch}
        )

    def create_commit(self, file_path, branch, content, commit_message):
        file = self.project.files.get(file_path, ref=branch)
        file.content = content
        file.save(branch=branch, commit_message=commit_message)

    def get_pr(self, pr_id):
        # TODO normalize the return value between providers
        return self.project.mergerequests.get(pr_id)

    def get_file(self, file_path, branch_name):
        file = self.project.files.get(file_path, ref=branch_name)
        content = base64.b64decode(file.content).decode("UTF-8")
        return content

    def create_pr(self, source_branch, target_branch, title, description):
        return self.project.mergerequests.create(
            {
                "source_branch": source_branch,
                "target_branch": target_branch,
                "title": title,
                "description": description,
            }
        )

    def create_pr_comment(self, pr_id, comment):
        merge_request = self.project.mergerequests.get(pr_id)

        merge_request.notes.create({"body": comment})
