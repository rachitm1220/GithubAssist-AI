import streamlit as st
import requests
import base64
from authorization_file_content import get_headers

GITHUB_API_BASE = "https://api.github.com"


def create_file(repo_full_name, path, content, commit_message):
    url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/contents/{path}"
    content_encoded = base64.b64encode(content).decode("utf-8")
    payload = {
        "message": commit_message,
        "content": content_encoded
    }
    response = requests.put(url, json=payload, headers=get_headers())
    if response.status_code == 201:
        return response.json()
    elif response.status_code == 422:
        st.error("⚠️ A file with this name already exists at this path.")
    else:
        st.error(f"❌ Failed to create file: {response.status_code} {response.text}")
    return None
