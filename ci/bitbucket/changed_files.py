import os
import requests

BITBUCKET_ACCESS_TOKEN = os.environ.get("BITBUCKET_ACCESS_TOKEN_PIXEE")
BITBUCKET_REPO_SLUG = os.environ.get("BITBUCKET_REPO_SLUG")
BITBUCKET_WORKSPACE = os.environ.get("BITBUCKET_WORKSPACE")
API_URL = os.environ.get("BITBUCKET_API_URL") or "https://api.bitbucket.org/2.0/"
BITBUCKET_PR_ID = os.environ.get("BITBUCKET_PR_ID")

# URL to fetch the diffstat link from the pull request
url = f"{API_URL}repositories/{BITBUCKET_WORKSPACE}/{BITBUCKET_REPO_SLUG}/pullrequests/{BITBUCKET_PR_ID}/"

headers = {
    "Authorization": f"Bearer {BITBUCKET_ACCESS_TOKEN}",
    "Accept": "application/json",
}

# Make the first API call to get the diffstat URL
response = requests.get(url, headers=headers, timeout=10)
data = response.json()
diffstat_url = data["links"]["diffstat"]["href"]

# Make the second API call using the diffstat URL
diffstat_response = requests.get(
    f"{diffstat_url}&fields=values.new.path", headers=headers, timeout=10
)
diffstat_data = diffstat_response.json()

# Extract the new path from each file in the diffstat and join them with commas
file_paths = [item["new"]["path"] for item in diffstat_data["values"]]
print(",".join(file_paths))
