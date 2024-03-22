from dotenv import load_dotenv
import os

load_dotenv()

from git_service import GitService
from gitlab_provider import GitLabProvider


gitlab_token = os.environ.get("GITLAB_API_TOKEN_PIXEE")
gitlab_project_id = os.environ.get("GITLAB_PROJECT_ID")


git_service = GitService(GitLabProvider(gitlab_project_id, gitlab_token))
