import os
import gitlab
import sys
import json
import whatthepatch
import base64
import secrets


# GitLab settings

gitlab_url = os.environ.get("GITLAB_API_URL", "https://gitlab.com")

api_token = os.environ.get("GITLAB_API_TOKEN_PIXEE")
project_id = os.environ.get("CI_MERGE_REQUEST_PROJECT_ID") or os.environ.get(
    "CI_PROJECT_ID"
)
source_branch = os.environ.get("CI_MERGE_REQUEST_SOURCE_BRANCH_NAME") or os.environ.get(
    "CI_COMMIT_REF_NAME"
)
new_branch_name = "pixee_" + str(
    secrets.SystemRandom().randint(0, 1000)
)  # Replace with the desired new branch name
merge_id = os.environ.get("CI_MERGE_REQUEST_IID")

source_title = os.environ.get("CI_MERGE_REQUEST_TITLE") or os.environ.get(
    "CI_PROJECT_NAME"
)


def main():
    filename = str(sys.argv[1])
    # working_dir = os.path.dirname(os.path.abspath(filename))

    with open(filename, "r", encoding="utf-8") as file:
        data = json.load(file)

    # Initialize GitLab client
    gl = gitlab.Gitlab(gitlab_url, private_token=api_token)

    # Create a new branch based on an existing branch
    project = gl.projects.get(project_id)
    branch = project.branches.create({"branch": new_branch_name, "ref": source_branch})

    print(f"Created a new branch: {branch.name}")

    description = ""

    has_change = False

    for result in data["results"]:
        if len(result["changeset"]):
            print(result["summary"])

            description = (
                description
                + f"""
## {result["summary"]}

{result["description"]}
"""
            )
            print(description)

            for entry in result["changeset"]:
                try:
                    print(entry["path"])

                    file = project.files.get(entry["path"], ref=new_branch_name)
                    original_file_content = base64.b64decode(file.content).decode()

                    diff = [x for x in whatthepatch.parse_patch(entry["diff"])]
                    diff = diff[0]

                    new_file = whatthepatch.apply_diff(
                        diff, original_file_content, use_patch=True
                    )
                    new_file = "\n".join(new_file[0])

                    file.content = new_file
                    file.save(branch=new_branch_name, commit_message=result["summary"])
                    has_change = True

                except Exception as e:
                    print("The error is: ", e)
    if has_change:
        new_mr = project.mergerequests.create(
            {
                "source_branch": new_branch_name,
                "target_branch": source_branch,
                "title": f"Pixee Hardening Suggestions for {source_title}",
                "description": description,
            }
        )
        print(f"Hardening Suggestions for {source_branch}")
        print(new_mr.web_url)

        if merge_id:
            merge_request = project.mergerequests.get(merge_id)

            # Add a comment to the merge request
            merge_request.notes.create(
                {
                    "body": f"Pixee has created some suggestions in: [Hardening Suggestions for {source_branch}]({new_mr.web_url})"
                }
            )
    else:
        print("No changes made.")


if __name__ == "__main__":
    main()
