import json
import joblib
import sys
import os
import requests
from gemini import get_pr_fix_suggestions
from github_status import set_github_status

# Load the trained model
model = joblib.load('./buggy_pr_classifier.pkl')

# GitHub environment variables
repo = os.environ.get("GITHUB_REPOSITORY")      
commit_sha = os.environ.get("GITHUB_SHA")           
github_token = os.environ.get("GITHUB_TOKEN")

# GitHub API URL to fetch PR data by commit
pr_api_url = f"https://api.github.com/repos/{repo}/commits/{commit_sha}/pulls"

# Headers to authenticate with GitHub API
headers = {
    "Authorization": f"token {github_token}",
    "Accept": "application/vnd.github.groot-preview+json"  # Needed for commit→PR mapping
}

# Fetch PRs associated with the commit
response = requests.get(pr_api_url, headers=headers)

if response.status_code == 200:
    pr_list = response.json()
    if not pr_list:
        print("No pull requests found for this commit.")
        sys.exit(1)
    pr_data = pr_list[0]  # Use the first associated PR
else:
    print(f"Failed to fetch PR data: {response.status_code}")
    sys.exit(1)

# Extract features from the PR data
def extract_features(pr_data):
    features = {}

    # Get title and description lengths
    features['title_len'] = len(pr_data.get('title', ""))
    features['desc_len'] = len(pr_data.get('body', ""))
    
    # Status mapping
    status_map = {"open": 0, "closed": 1}
    features['status'] = status_map.get(pr_data.get('state', '').lower(), -1)
    
    # Other features
    features['num_comments'] = pr_data.get('comments', 0)
    features['num_additions'] = pr_data.get('additions', 0)
    features['num_deletions'] = pr_data.get('deletions', 0)
    features['num_changed_files'] = pr_data.get('changed_files', 1)
    features['num_commits'] = pr_data.get('commits', 0)
    features['was_closed'] = 1 if pr_data.get('state', '') == "closed" else 0

    return features

# Extract features
features = extract_features(pr_data)

# Prepare the input for the model
X_input = [
    features['title_len'],
    features['desc_len'],
    features['status'],
    features['num_comments'],
    features['num_additions'],
    features['num_deletions'],
    features['num_commits'],
    features['was_closed'],
    features['num_changed_files']
]

# Make prediction
pred = model.predict([X_input])[0]
risk_score = model.predict_proba([X_input])[0][1]  # Probability of being buggy

# Get PR title & description for fix suggestion
pr_title = pr_data.get('title', "")
pr_description = pr_data.get('body', "")

try:
    suggestion = get_pr_fix_suggestions(pr_title, pr_description)
    print("Fix Suggestions:\n", suggestion)
except Exception as e:
    suggestion = f"Error fetching suggestions: {str(e)}"
    print(suggestion)

# Output result as JSON
result = {"prediction": int(pred), "risk_score": risk_score}

# Set GitHub commit status based on risk score
if risk_score > 0.9:
    set_github_status(repo, commit_sha, "failure", "Bug risk > 90%. Fix required.", "AI Bug Reviewer", github_token)
else:
    set_github_status(repo, commit_sha, "success", "PR looks clean", "AI Bug Reviewer", github_token)

print(json.dumps(result))
