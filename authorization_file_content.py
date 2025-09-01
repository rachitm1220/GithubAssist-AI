import streamlit as st
import requests
import base64

GITHUB_API_BASE = "https://api.github.com"

def request_github_token():
    if "github_token" not in st.session_state:
        token = st.text_input("Enter your GitHub Personal Access Token", type="password")
        if token:
            st.session_state.github_token = token.strip()
            st.rerun()
        else:
            st.warning("Please enter a valid GitHub Personal Access Token.")
            st.stop()
    return st.session_state.github_token

def get_headers():
    return {
        "Authorization": f"token {st.session_state.github_token}"
    }

def list_repos():
    url = f"{GITHUB_API_BASE}/user/repos"
    response = requests.get(url, headers=get_headers())
    if response.status_code != 200:
        st.error(f"Failed to list repos: {response.status_code} {response.text}")
        return []
    repos = response.json()
    return [repo["full_name"] for repo in repos]

def get_repo_contents(repo_full_name, path=""):
    url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/contents/{path}"
    response = requests.get(url, headers=get_headers())
    if response.status_code == 404:
        return []
    elif response.status_code != 200:
        st.error(f"Failed to get contents: {response.status_code} {response.text}")
        return []
    return response.json()

def get_file_content(repo_full_name, path):
    data = get_repo_contents(repo_full_name, path)
    if isinstance(data, dict) and "content" in data:
        content = base64.b64decode(data["content"]).decode('utf-8')
        sha = data["sha"]
        return content, sha
    return None, None

def update_file(repo_full_name, path, new_content, sha, commit_message):
    url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/contents/{path}"
    content_encoded = base64.b64encode(new_content.encode("utf-8")).decode("utf-8")
    payload = {
        "message": commit_message,
        "content": content_encoded,
        "sha": sha
    }
    response = requests.put(url, json=payload, headers=get_headers())
    if response.status_code not in [200, 201]:
        st.error(f"Failed to update file: {response.status_code} {response.text}")
        return None
    return response.json()