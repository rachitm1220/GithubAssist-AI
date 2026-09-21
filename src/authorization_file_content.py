import base64
import streamlit as st
import requests

GITHUB_API_BASE = "https://api.github.com"


def request_github_token():
    """
    Render the GitHub token input in the sidebar and return the stored token
    (or None if not yet provided, in which case the caller should stop).
    """
    if "github_token" not in st.session_state:
        st.session_state.github_token = ""

    with st.sidebar:
        token = st.text_input(
            "GitHub Personal Access Token",
            type="password",
            value=st.session_state.github_token,
            help="Needs the 'repo' scope to read/write private repositories.",
            placeholder="ghp_xxxxxxxxxxxxxxxxxxxx",
        )
        if token != st.session_state.github_token:
            st.session_state.github_token = token.strip()
            st.session_state.pop("repo_list_cache", None)
            st.rerun()

    return st.session_state.github_token or None


def get_headers():
    return {
        "Authorization": f"token {st.session_state.github_token}",
        "Accept": "application/vnd.github+json",
    }


@st.cache_data(show_spinner=False, ttl=120)
def _fetch_repos(token: str):
    url = f"{GITHUB_API_BASE}/user/repos?per_page=100&sort=updated"
    response = requests.get(url, headers={"Authorization": f"token {token}", "Accept": "application/vnd.github+json"})
    if response.status_code != 200:
        return None, f"{response.status_code} {response.text}"
    return [repo["full_name"] for repo in response.json()], None


def list_repos():
    token = st.session_state.get("github_token")
    if not token:
        return []
    repos, error = _fetch_repos(token)
    if error:
        st.error(f"Failed to list repos: {error}")
        return []
    return repos or []


def get_repo_contents(repo_full_name, path=""):
    url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/contents/{path}"
    response = requests.get(url, headers=get_headers())
    if response.status_code == 404:
        return []
    elif response.status_code != 200:
        st.error(f"Failed to get contents: {response.status_code} {response.text}")
        return []
    data = response.json()
    # A single-file path returns a dict, not a list — normalize to a list for callers
    return data if isinstance(data, list) else [data]


def get_file_content(repo_full_name, path):
    url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/contents/{path}"
    response = requests.get(url, headers=get_headers())
    if response.status_code != 200:
        st.error(f"Failed to fetch file: {response.status_code} {response.text}")
        return None, None
    data = response.json()
    if isinstance(data, dict) and "content" in data:
        content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        return content, data["sha"]
    return None, None


def update_file(repo_full_name, path, new_content, sha, commit_message):
    url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/contents/{path}"
    content_encoded = base64.b64encode(new_content.encode("utf-8")).decode("utf-8")
    payload = {
        "message": commit_message,
        "content": content_encoded,
        "sha": sha,
    }
    response = requests.put(url, json=payload, headers=get_headers())
    if response.status_code not in (200, 201):
        st.error(f"Failed to update file: {response.status_code} {response.text}")
        return None
    return response.json()
