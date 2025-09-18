import streamlit as st
import requests
import base64
import subprocess
from authorization_file_content import request_github_token, get_headers, list_repos, get_repo_contents, get_file_content, update_file
from upload_file import create_file
from type_detection import detect_file_type
from rename_files import rename_file, rename_folder
from agent import agent_graph

config = {"configurable": {"thread_id": "1"}}
GITHUB_API_BASE = "https://api.github.com"

# Formatter for Python (using Black)
def format_code_python(code):
    try:
        result = subprocess.run(['black', '-'], input=code, text=True, capture_output=True)
        if result.returncode == 0:
            return result.stdout
        else:
            raise Exception("Formatting failed.")
    except Exception as e:
        st.error(f"⚠️ Error formatting Python code: {str(e)}")
        return code

# Formatter for JavaScript, HTML, and CSS (using Prettier)
def format_code_js(code):
    try:
        result = subprocess.run(['prettier', '--stdin'], input=code, text=True, capture_output=True)
        if result.returncode == 0:
            return result.stdout
        else:
            raise Exception("Formatting failed.")
    except Exception as e:
        st.error(f"⚠️ Error formatting JavaScript code: {str(e)}")
        return code

def main():
    st.info("🔐 Note: Your GitHub token must have 'repo' scope to read/write private repositories.")

    token = request_github_token()
    repos = list_repos()
    if not repos:
        st.warning("No repositories found or unable to fetch. Check token permissions.")
        return

    if "gemini_memory" not in st.session_state:
        st.session_state.gemini_memory = {}

    repo_names = [repo.split("/")[-1] for repo in repos]
    repo_selected_name = st.selectbox("📦 Select a repository", repo_names)
    repo_full_name = next((r for r in repos if r.endswith(f"/{repo_selected_name}")), None)
    if not repo_full_name:
        st.error("❌ Could not determine full repo name.")
        st.stop()

    if "path_stack" not in st.session_state:
        st.session_state.path_stack = []

    if st.session_state.path_stack:
        if st.button("⬆ Go up one directory"):
            st.session_state.path_stack.pop()

    current_path = "/".join(st.session_state.path_stack)
    contents = get_repo_contents(repo_full_name, current_path)

    folders = [item for item in contents if item["type"] == "dir"]
    files = [item for item in contents if item["type"] == "file"]

    folder_names = [folder["name"] for folder in folders]
    file_names = [file["name"] for file in files]

    # Folder rename UI
    if folder_names:
        folder_selected = st.selectbox("📁 Navigate into folder", ["-- Select folder --"] + folder_names)
        if folder_selected and folder_selected != "-- Select folder --":
            st.session_state.path_stack.append(folder_selected)
            st.rerun()

        folder_to_rename = st.text_input("✏️ Enter folder name to rename")
        if folder_to_rename and folder_to_rename != "-- None --":
            new_folder_name = st.text_input(f"📝 New name for folder '{folder_to_rename}'")
            if new_folder_name and new_folder_name != folder_to_rename:
                if st.button(f"🔄 Rename folder '{folder_to_rename}' to '{new_folder_name}'"):
                    old_folder_path = "/".join(st.session_state.path_stack + [folder_to_rename])
                    rename_folder(repo_full_name, old_folder_path, new_folder_name, f"Rename folder {folder_to_rename} to {new_folder_name}")
                    st.success(f"Folder renamed to '{new_folder_name}'.")
                    st.rerun()

    file_selected = None
    if file_names:
        file_selected = st.selectbox("📄 Select File to Edit", file_names)

        if file_selected:
            new_file_name = st.text_input(f"📝 New name for file '{file_selected}'")
            if new_file_name and new_file_name != file_selected:
                if st.button(f"🔄 Rename file '{file_selected}' to '{new_file_name}'"):
                    old_file_path = "/".join(st.session_state.path_stack + [file_selected])
                    new_file_path = "/".join(st.session_state.path_stack + [new_file_name])
                    rename_file(repo_full_name, old_file_path, new_file_path, f"Rename file {file_selected} to {new_file_name}")
                    st.success(f"File renamed to '{new_file_name}'.")
                    st.rerun()

    if file_selected:
        full_file_path = "/".join(st.session_state.path_stack + [file_selected])
        detected_type = detect_file_type(file_selected)
        st.info(f"🧠 Detected File Type: {detected_type}")

        content, sha = get_file_content(repo_full_name, full_file_path)

        if content is not None:
            if full_file_path not in st.session_state.gemini_memory:
                st.session_state.gemini_memory[full_file_path] = {
                    "original_code": content,
                    "improved_code": content,
                    "commit_message": "",
                    "review_result": None,
                }

            edited_content = st.text_area("✏️ Edit file content", st.session_state.gemini_memory[full_file_path]["improved_code"], height=400)
            commit_msg = st.text_input("💬 Commit message", "Edited file via Streamlit")

            format_toggle = st.checkbox("✅ Auto-format the code before committing", value=True)

            if format_toggle:
                if detected_type == "python":
                    edited_content = format_code_python(edited_content)
                elif detected_type in ["javascript", "html", "css"]:
                    edited_content = format_code_js(edited_content)

            if st.button("✅ Commit changes"):
                if commit_msg.strip() == "":
                    st.error("❗ Commit message cannot be empty.")
                else:
                    result = update_file(repo_full_name, full_file_path, edited_content, sha, commit_msg)
                    if result:
                        st.success("✅ File updated and committed successfully!")
                        st.session_state.gemini_memory[full_file_path]["improved_code"] = edited_content
                        st.session_state.gemini_memory[full_file_path]["commit_message"] = commit_msg
                        st.rerun()

            # --- New Button: Review with Gemini ---
            if st.button("💡 Review with Gemini"):
                with st.spinner("🔧 Gemini is reviewing your code..."):
                    agent = agent_graph()
                    current_code_for_review = st.session_state.gemini_memory[full_file_path]["improved_code"]
                    state = {
                        "file_name": file_selected,
                        "file_type": detected_type,
                        "file_content": current_code_for_review,
                    }
                    result = agent.invoke(state, config)

                    st.session_state.gemini_memory[full_file_path]["review_result"] = result

            review_result = st.session_state.gemini_memory[full_file_path].get("review_result")
            if review_result:
                improved_code = review_result.get("improved_code")
                corrections_summary = review_result.get("corrections_summary")

                if improved_code and corrections_summary:
                    st.success("✅ Gemini provided an improved version of your code.")
                    st.text_area("🆕 Improved Code", improved_code, height=400, key="gemini_improved_code_preview")
                    st.text_area("🛠️ Changes Made", corrections_summary, height=300)

                    gemini_commit_msg = st.text_input("💬 Commit message for Gemini changes", "Committed improvements from Gemini code review")

                    if st.button("✅ Commit Gemini changes"):
                        if gemini_commit_msg.strip() == "":
                            st.error("❗ Commit message cannot be empty.")
                        else:
                            _, latest_sha = get_file_content(repo_full_name, full_file_path)
                            result = update_file(repo_full_name, full_file_path, improved_code, latest_sha, gemini_commit_msg)

                            if result:
                                st.success("✅ File updated and committed successfully!")
                                st.session_state.gemini_memory[full_file_path]["improved_code"] = improved_code
                                st.session_state.gemini_memory[full_file_path]["commit_message"] = gemini_commit_msg
                                st.rerun()
                            else:
                                st.error("❌ Failed to commit changes. Check logs or GitHub token.")
                else:
                    st.error("❌ Gemini couldn't generate an improvement.")
        else:
            st.warning("⚠️ Cannot fetch file content.")
    else:
        st.info("ℹ️ No files found in this directory.")

    # --- Upload Section ---
    st.markdown("---")
    st.subheader("📤 Upload New File")

    uploaded_file = st.file_uploader("Choose a file to upload", type=None)
    new_file_commit_msg = st.text_input("📝 Commit message for new file", "Add new file via Streamlit", key="upload_commit_msg")

    if uploaded_file is not None:
        if new_file_commit_msg.strip() == "":
            st.error("❗ Commit message cannot be empty.")
        else:
            new_file_path = "/".join(st.session_state.path_stack + [uploaded_file.name])
            file_bytes = uploaded_file.read()
            if st.button("🚀 Upload file"):
                result = create_file(repo_full_name, new_file_path, file_bytes, new_file_commit_msg)
                if result:
                    st.success("✅ File uploaded and committed successfully!")
                    st.rerun()

    # --- Debugging: Show memory ---
    with st.expander("🧠 Gemini Code History (Session Memory)", expanded=False):
        st.json(st.session_state.gemini_memory)

if __name__ == "__main__":
    main()
