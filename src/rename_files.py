import streamlit as st
import requests
import base64
from authorization_file_content import request_github_token, get_headers, list_repos, get_repo_contents, get_file_content, update_file
from upload_file import create_file
from type_detection import detect_file_type

GITHUB_API_BASE = "https://api.github.com"

def delete_file(repo_full_name, path, sha, commit_message):
    """Delete a file from GitHub repo."""
    url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/contents/{path}"
    payload = {
        "message": commit_message,
        "sha": sha,
    }
    response = requests.delete(url, json=payload, headers=get_headers())
    if response.status_code != 200:
        st.error(f"Failed to delete file: {response.status_code} {response.text}")
        return None
    return response.json()


def rename_file(repo_full_name, old_path, new_path, commit_message):
    """
    Rename a file by copying it to new_path and deleting the old file.
    """
    content, sha = get_file_content(repo_full_name, old_path)
    if content is None:
        st.error("Cannot fetch original file content to rename.")
        return None

    # Create new file with same content
    create_resp = create_file(repo_full_name, new_path, content.encode("utf-8"), commit_message)
    if create_resp is None:
        st.error("Failed to create new file for rename.")
        return None

    # Delete old file
    delete_resp = delete_file(repo_full_name, old_path, sha, commit_message)
    if delete_resp is None:
        st.error("Failed to delete old file after rename.")
        return None

    return True


def rename_folder(repo_full_name, old_folder_path, new_folder_name, commit_message):
    """
    Rename a folder by renaming all files inside to new folder path.
    """
    # Fetch all files recursively inside the folder
    def fetch_all_files_recursive(repo_full_name, path):
        contents = get_repo_contents(repo_full_name, path)
        if not contents:
            return []
        files = []
        for item in contents:
            if item["type"] == "file":
                files.append(item["path"])
            elif item["type"] == "dir":
                files.extend(fetch_all_files_recursive(repo_full_name, item["path"]))
        return files

    files_to_rename = fetch_all_files_recursive(repo_full_name, old_folder_path)
    if not files_to_rename:
        st.warning("Folder is empty or does not exist.")
        return None

    new_folder_path = "/".join(old_folder_path.split("/")[:-1] + [new_folder_name])

    for old_file_path in files_to_rename:
        # Calculate new file path with new folder name
        relative_path = old_file_path[len(old_folder_path):].lstrip("/")
        new_file_path = f"{new_folder_path}/{relative_path}" if relative_path else new_folder_path

        rename_file(repo_full_name, old_file_path, new_file_path, commit_message)

    return True
