from bitbucket_client import BitbucketClient
from secrets import token_hex
from dotenv import load_dotenv
import os
import sys
import json
import whatthepatch

load_dotenv()

api_token = os.environ.get("BITBUCKET_ACCESS_TOKEN_PIXEE")
repository_slug = os.environ.get("BITBUCKET_REPO_SLUG")
workspace = os.environ.get("BITBUCKET_WORKSPACE")
api_url = os.environ.get("BITBUCKET_API_URL") or "https://api.bitbucket.org/2.0/"
workspace = os.environ.get("BITBUCKET_WORKSPACE")
pull_request_id = os.environ.get("BITBUCKET_PR_ID")

filename = str(sys.argv[1])

with open(filename, "r", encoding="utf-8") as file:
    data = json.load(file)

bitbucket = BitbucketClient(api_token, api_url)

# get info about the current pull request
pull_request_info = bitbucket.get_pull_request_info(
    workspace, repository_slug, pull_request_id
)
source_title = pull_request_info["title"]
pr_title = f"Hardening Suggestions for: '{source_title}'."

# create a new branch with a unique name
new_branch_name = f"pixee_{pull_request_id}_{token_hex(4)}"

destination_branch = pull_request_info["source"]["branch"]["name"]
bitbucket.create_branch(workspace, repository_slug, new_branch_name, destination_branch)


description = ""

made_change = False

for result in data["results"]:
    if len(result["changeset"]):
        # print(result["summary"])
        description = "## {}\n{}\n\n".format(result["summary"], result["description"])

        if len(result["changeset"]) >= 1:
            made_change = True

        for entry in result["changeset"]:
            try:
                original_file_content = bitbucket.read_file(
                    workspace, repository_slug, entry["path"], new_branch_name
                )
                original_file_content = original_file_content.decode("UTF-8")

                diff = list(whatthepatch.parse_patch(entry["diff"]))
                diff = diff[0]

                new_file = whatthepatch.apply_diff(
                    diff, original_file_content, use_patch=True
                )
                new_file = "\n".join(new_file[0])

                bitbucket.commit_file(
                    workspace,
                    repository_slug,
                    entry["path"],
                    new_branch_name,
                    result["summary"],
                    new_file,
                )

            except Exception as e:
                print("The error is: ", e)

if made_change:
    new_pr = bitbucket.create_pull_request(
        workspace,
        repository_slug,
        pr_title,
        description,
        new_branch_name,
        destination_branch,
    )
    pr_link = new_pr["links"]["html"]["href"]

    # Markdown formatted comment TODO add URL to new PR
    comment = f"""
    Pixee has reviewed the code made [some suggestions]({pr_link}).
    """

    result = bitbucket.add_comment_to_pull_request(
        workspace, repository_slug, pull_request_id, comment
    )
else:
    print("No changes made.")
    sys.exit(0)
