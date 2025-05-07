import requests
#comments are added to this file
def set_github_status(repo, sha, state, description, context, github_token):
    url = f"https://api.github.com/repos/{repo}/statuses/{sha}"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json"
    }
    data = {
        "state": state,  # 'success', 'failure', or 'pending'
        "description": description,
        "context": context
    }

    response = requests.post(url, headers=headers, json=data)
    if response.status_code != 201:
        print("Failed to set status:", response.status_code, response.text)
    else:
        print("Status set to:", state)
