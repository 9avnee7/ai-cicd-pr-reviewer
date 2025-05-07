import json
import joblib
import sys
import os
import requests
from gemini import get_pr_fix_suggestions
from github_status import set_github_status

# Load the trained model
model = joblib.load('./buggy_pr_classifier.pkl')

repo = os.environ.get("GITHUB_REPOSITORY")
commit_sha = os.environ.get("GITHUB_SHA")
github_token = os.environ.get("GITHUB_TOKEN")

# GitHub API URL to fetch PRs associated with the commit
pr_api_url = f"https://api.github.com/repos/{repo}/commits/{commit_sha}/pulls"

headers = {
    "Authorization": f"token {github_token}",
    "Accept": "application/vnd.github.groot-preview+json"
}

response = requests.get(pr_api_url, headers=headers)

if response.status_code != 200 or not response.json():
    print(f"Failed to fetch PR data: {response.status_code}")
    sys.exit(1)

# If multiple PRs, take the first
pr_data_raw = response.json()[0]

# Get full PR details using PR number
pr_number = pr_data_raw['number']
pr_url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
pr_detail_resp = requests.get(pr_url, headers=headers)
if pr_detail_resp.status_code != 200:
    print(f"Failed to fetch detailed PR info: {pr_detail_resp.status_code}")
    sys.exit(1)

pr_data = pr_detail_resp.json()

def extract_features(pr_data):
    return {
        'title_len': len(pr_data.get('title', "")),
        'desc_len': len(pr_data.get('body', "")),
        'status': {"open": 0, "closed": 1}.get(pr_data.get('state', '').lower(), -1),
        'num_comments': pr_data.get('comments', 0),
        'num_additions': pr_data.get('additions', 0),
        'num_deletions': pr_data.get('deletions', 0),
        'num_changed_files': pr_data.get('changed_files', 1),
        'num_commits': pr_data.get('commits', 0),
        'was_closed': 1 if pr_data.get('state', '') == "closed" else 0,
    }

features = extract_features(pr_data)
X_input = [features[k] for k in ['title_len', 'desc_len', 'status', 'num_comments',
                                 'num_additions', 'num_deletions', 'num_commits',
                                 'was_closed', 'num_changed_files']]

# Prediction
pred = model.predict([X_input])[0]
risk_score = model.predict_proba([X_input])[0][1]

pr_title = pr_data.get('title', "")
pr_description = pr_data.get('body', "")
try:
    suggestion = get_pr_fix_suggestions(pr_title, pr_description)
except Exception as e:
    suggestion = f"Error fetching suggestions: {str(e)}"

# Set GitHub status
if risk_score > 0.9:
    set_github_status(repo, commit_sha, "failure", "Bug risk > 90%. Fix required.", "AI Bug Reviewer", github_token)
    print("Suggestions:\n", suggestion)
else:
    set_github_status(repo, commit_sha, "success", "PR looks clean", "AI Bug Reviewer", github_token)

print(json.dumps({"prediction": int(pred), "risk_score": risk_score}))
