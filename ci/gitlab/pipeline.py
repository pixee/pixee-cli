import os
import gitlab
import sys
import json
import whatthepatch
import base64
import secrets


# GitLab settings
gitlab_url = "https://gitlab.com"  # Replace with your GitLab URL
api_token = os.environ.get('API_TOKEN')
project_id = os.environ.get('CI_MERGE_REQUEST_PROJECT_ID')
source_branch = os.environ.get('CI_MERGE_REQUEST_SOURCE_BRANCH_NAME')
new_branch_name = "pixee_" + str(secrets.SystemRandom().randint(0, 1000))  # Replace with the desired new branch name
merge_id = os.environ.get('CI_MERGE_REQUEST_IID')

source_title = os.environ.get('CI_MERGE_REQUEST_TITLE')

def main():
    for name, value in os.environ.items():
        print("{0}: {1}".format(name, value))
    
    filename = str(sys.argv[1])
    #working_dir = os.path.dirname(os.path.abspath(filename))
    
    with open(filename, 'r', encoding="utf-8") as file:
        data = json.load(file)

    # Initialize GitLab client
    gl = gitlab.Gitlab(gitlab_url, private_token=api_token)

    # Create a new branch based on an existing branch
    project = gl.projects.get(project_id)
    branch = project.branches.create(
        {"branch": new_branch_name, "ref": source_branch}
    )

    print(f"Created a new branch: {branch.name}")
    
    description = ""
    
    for result in data["results"]:
        if len(result["changeset"]):
            print(result["summary"])
        
            description = description + f"""
## {result["summary"]}

{result["description"]}
"""
            print(description)
    
            for entry in result["changeset"]:
                try:
                    print(entry["path"])
        
                    file = project.files.get(entry["path"], ref=new_branch_name)
                    original_file_content = base64.b64decode(file.content).decode()
        
                    diff = [x for x in whatthepatch.parse_patch(entry["diff"])]
                    diff = diff[0]
        
                    new_file = whatthepatch.apply_diff(diff, original_file_content, use_patch=True)
                    new_file = "\n".join(new_file[0])
        
        
                    file.content = new_file
                    file.save(
                        branch=new_branch_name,
                        commit_message=result["summary"]
                    )
                    print(file)
                except Exception as e:
                    print("The error is: ",e)

    new_mr = project.mergerequests.create(
        {
            "source_branch": new_branch_name,
            "target_branch": source_branch,
            "title": f"Hardening Suggestions for {source_title}",
            "description": description,
        }
    )
    print(f"Hardening Suggestions for {source_branch}")
    print(new_mr.web_url)

    merge_request = project.mergerequests.get(merge_id)

    # Add a comment to the merge request
    merge_request.notes.create({'body': f"Pixee has created some suggestions in: [Hardening Suggestions for {source_branch}]({new_mr.web_url})" })
            

        #print(commit)
if __name__ == "__main__":
    main()
