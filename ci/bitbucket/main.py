from bitbucket_client import BitbucketClient
from pprint import pprint

from dotenv import load_dotenv
import os

load_dotenv()

api_token = os.environ.get("ACCESS_TOKEN")

project_key = os.environ.get("BITBUCKET_PROJECT_KEY")
repository_slug = os.environ.get("BITBUCKET_REPO_SLUG")
workspace = os.environ.get("BITBUCKET_WORKSPACE")
api_url = os.environ.get("BITBUCKET_API_URL") or "https://api.bitbucket.org/2.0/"
workspace = os.environ.get("BITBUCKET_WORKSPACE")

bitbucket = BitbucketClient(api_token)

new_branch_name = "pixee_test_matt_13"

source_title = "pixee test pr 1"
description = "test description"

destination_branch = "master"

# print(bitbucket.get_repo_info(workspace, repository_slug))
# print(bitbucket.create_branch(workspace, repository_slug, new_branch_name, "master"))
# content = bitbucket.read_file(workspace, repository_slug, "README.md", new_branch_name)
# content = content.decode('UTF-8')
# print(content)
# print(bitbucket.commit_file(workspace, repository_slug, "README.md", new_branch_name, "test", f"{content}\nthis is a test"))


result = bitbucket.create_pull_request(
    workspace,
    repository_slug,
    f"Hardening Suggestions for {source_title}",
    description,
    new_branch_name,
    destination_branch,
)
pprint(result)
