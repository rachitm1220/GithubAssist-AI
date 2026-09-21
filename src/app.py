import difflib
import subprocess

import streamlit as st

from authorization_file_content import (
    request_github_token,
    list_repos,
    get_repo_contents,
    get_file_content,
    update_file,
)
from upload_file import create_file
from type_detection import detect_file_type_details
from rename_files import rename_file, rename_folder
from agent import agent_graph

CONFIG = {"configurable": {"thread_id": "1"}}


# --------------------------------------------------------------------------------------
# Formatters
# --------------------------------------------------------------------------------------
def format_code_python(code: str) -> str:
    try:
        result = subprocess.run(["black", "-"], input=code, text=True, capture_output=True)
        if result.returncode == 0:
            return result.stdout
        st.warning("Black couldn't format this file (it may have syntax errors) — left it as-is.")
        return code
    except FileNotFoundError:
        st.warning("`black` isn't installed, so the Python file wasn't auto-formatted.")
        return code
    except Exception as e:
        st.warning(f"Formatting skipped: {e}")
        return code


def format_code_js(code: str) -> str:
    try:
        result = subprocess.run(["prettier", "--stdin-filepath", "file.js"], input=code, text=True, capture_output=True)
        if result.returncode == 0:
            return result.stdout
        st.warning("Prettier couldn't format this file — left it as-is.")
        return code
    except FileNotFoundError:
        st.warning("`prettier` isn't installed, so the file wasn't auto-formatted.")
        return code
    except Exception as e:
        st.warning(f"Formatting skipped: {e}")
        return code


def maybe_format(content: str, language: str, enabled: bool) -> str:
    if not enabled:
        return content
    if language == "python":
        return format_code_python(content)
    if language in ("javascript", "jsx", "typescript", "tsx", "html", "css"):
        return format_code_js(content)
    return content


# --------------------------------------------------------------------------------------
# Small UI helpers
# --------------------------------------------------------------------------------------
def render_breadcrumbs():
    stack = st.session_state.path_stack
    cols = st.columns([1] + [4] * (len(stack) + 1))

    with cols[0]:
        if st.button("🏠", help="Go to repository root", disabled=not stack, use_container_width=True):
            st.session_state.path_stack = []
            st.rerun()

    crumb_labels = ["root"] + stack
    for i, label in enumerate(crumb_labels):
        with cols[i + 1] if i + 1 < len(cols) else st.container():
            is_last = i == len(crumb_labels) - 1
            if is_last:
                st.markdown(f"**{label}**")
            else:
                if st.button(label, key=f"crumb_{i}"):
                    st.session_state.path_stack = stack[: i]
                    st.rerun()


def diff_view(original: str, updated: str) -> str:
    diff = difflib.unified_diff(
        original.splitlines(),
        updated.splitlines(),
        fromfile="original",
        tofile="improved",
        lineterm="",
    )
    return "\n".join(diff) or "No differences."


# --------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------
def main():
    st.set_page_config(
        page_title="GithubAssist AI",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        """
        <style>
            .block-container { padding-top: 2rem; }
            div[data-testid="stMetricValue"] { font-size: 1.4rem; }
            .stTabs [data-baseweb="tab-list"] { gap: 4px; }
            .stTabs [data-baseweb="tab"] {
                padding: 8px 16px;
                border-radius: 8px 8px 0 0;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("🤖 GithubAssist AI")
    st.caption("Browse, edit, and AI-review files in your GitHub repos — right from the browser.")

    # ---------------- Sidebar: auth + Gemini key + repo picker ----------------
    with st.sidebar:
        st.header("⚙️ Setup")

    token = request_github_token()
    if not token:
        st.info("👈 Enter a GitHub token in the sidebar to get started. It needs the **repo** scope.")
        st.stop()

    with st.sidebar:
        st.session_state.setdefault("google_api_key", "")
        st.session_state.google_api_key = st.text_input(
            "Gemini API Key (for AI review)",
            type="password",
            value=st.session_state.google_api_key,
            help="Only needed if you use the 'Review with Gemini' feature. "
                 "Can also be set via GOOGLE_API_KEY env var or st.secrets.",
        )

        st.divider()
        st.header("📦 Repository")

    with st.spinner("Loading repositories…"):
        repos = list_repos()

    if not repos:
        st.warning("No repositories found, or the token can't access any. Check the token's scopes.")
        st.stop()

    repo_names = [repo.split("/")[-1] for repo in repos]
    with st.sidebar:
        repo_selected_name = st.selectbox("Select a repository", repo_names)
    repo_full_name = next((r for r in repos if r.endswith(f"/{repo_selected_name}")), None)
    if not repo_full_name:
        st.error("Could not resolve the selected repository.")
        st.stop()

    # Reset browsing state when the repo changes
    if st.session_state.get("_current_repo") != repo_full_name:
        st.session_state._current_repo = repo_full_name
        st.session_state.path_stack = []

    st.session_state.setdefault("path_stack", [])
    st.session_state.setdefault("gemini_memory", {})

    with st.sidebar:
        st.divider()
        st.caption(f"Connected to **{repo_full_name}**")

    # ---------------- Browse pane ----------------
    render_breadcrumbs()

    current_path = "/".join(st.session_state.path_stack)
    with st.spinner("Loading contents…"):
        contents = get_repo_contents(repo_full_name, current_path)

    folders = sorted([item for item in contents if item["type"] == "dir"], key=lambda x: x["name"].lower())
    files = sorted([item for item in contents if item["type"] == "file"], key=lambda x: x["name"].lower())

    browse_tab, upload_tab = st.tabs(["📁 Browse & Edit", "📤 Upload"])

    # ================= Browse & Edit =================
    with browse_tab:
        left, right = st.columns([1, 2], gap="large")

        with left:
            st.subheader("Contents")

            if folders:
                for folder in folders:
                    if st.button(f"📁 {folder['name']}", key=f"open_{folder['name']}", use_container_width=True):
                        st.session_state.path_stack.append(folder["name"])
                        st.rerun()

            if files:
                file_labels = []
                for f in files:
                    _, emoji, _ = detect_file_type_details(f["name"])
                    file_labels.append(f"{emoji} {f['name']}")
                file_index = st.radio(
                    "Files",
                    options=list(range(len(files))),
                    format_func=lambda i: file_labels[i],
                    label_visibility="collapsed",
                    key=f"file_radio_{current_path}",
                ) if files else None
                file_selected = files[file_index]["name"] if file_index is not None else None
            else:
                file_selected = None

            if not folders and not files:
                st.info("This folder is empty.")

            if folders or files:
                st.divider()
                with st.expander("✏️ Rename"):
                    if folders:
                        folder_to_rename = st.selectbox(
                            "Folder", ["—"] + [f["name"] for f in folders], key="folder_rename_select"
                        )
                        if folder_to_rename != "—":
                            new_folder_name = st.text_input("New folder name", key="new_folder_name")
                            if st.button("Rename folder", disabled=not new_folder_name or new_folder_name == folder_to_rename):
                                old_path = "/".join(st.session_state.path_stack + [folder_to_rename])
                                with st.spinner("Renaming folder…"):
                                    rename_folder(repo_full_name, old_path, new_folder_name, f"Rename {folder_to_rename} to {new_folder_name}")
                                st.success(f"Renamed folder to '{new_folder_name}'.")
                                st.rerun()

                    if files:
                        file_to_rename = st.selectbox(
                            "File", ["—"] + [f["name"] for f in files], key="file_rename_select"
                        )
                        if file_to_rename != "—":
                            new_file_name = st.text_input("New file name", key="new_file_name")
                            if st.button("Rename file", disabled=not new_file_name or new_file_name == file_to_rename):
                                old_path = "/".join(st.session_state.path_stack + [file_to_rename])
                                new_path = "/".join(st.session_state.path_stack + [new_file_name])
                                with st.spinner("Renaming file…"):
                                    rename_file(repo_full_name, old_path, new_path, f"Rename {file_to_rename} to {new_file_name}")
                                st.success(f"Renamed file to '{new_file_name}'.")
                                st.rerun()

        with right:
            if not file_selected:
                st.info("Select a file on the left to view and edit it.")
            else:
                full_file_path = "/".join(st.session_state.path_stack + [file_selected])
                label, emoji, language = detect_file_type_details(file_selected)

                header_l, header_r = st.columns([3, 1])
                with header_l:
                    st.subheader(f"{emoji} {file_selected}")
                    st.caption(f"{label} · `{full_file_path}`")

                with st.spinner("Fetching file…"):
                    content, sha = get_file_content(repo_full_name, full_file_path)

                if content is None:
                    st.warning("Couldn't load this file's content (it may be binary or too large).")
                else:
                    mem = st.session_state.gemini_memory.setdefault(
                        full_file_path,
                        {"original_code": content, "improved_code": content, "commit_message": "", "review_result": None},
                    )

                    edit_tab, preview_tab, ai_tab = st.tabs(["✏️ Edit", "👁️ Preview", "💡 AI Review"])

                    # ---- Edit ----
                    with edit_tab:
                        edited_content = st.text_area(
                            "File content", mem["improved_code"], height=420, key=f"editor_{full_file_path}"
                        )
                        format_toggle = st.checkbox("Auto-format before committing", value=True, key=f"fmt_{full_file_path}")
                        commit_msg = st.text_input("Commit message", "Edited file via GithubAssist AI", key=f"commit_{full_file_path}")

                        c1, c2 = st.columns([1, 1])
                        with c1:
                            if st.button("✅ Commit changes", type="primary", use_container_width=True, key=f"commit_btn_{full_file_path}"):
                                if not commit_msg.strip():
                                    st.error("Commit message cannot be empty.")
                                else:
                                    to_commit = maybe_format(edited_content, language, format_toggle)
                                    with st.spinner("Committing to GitHub…"):
                                        result = update_file(repo_full_name, full_file_path, to_commit, sha, commit_msg)
                                    if result:
                                        st.success("File updated and committed.")
                                        mem["improved_code"] = to_commit
                                        mem["commit_message"] = commit_msg
                                        st.rerun()
                        with c2:
                            if st.button("↩️ Reset to original", use_container_width=True, key=f"reset_{full_file_path}"):
                                mem["improved_code"] = mem["original_code"]
                                st.rerun()

                    # ---- Preview ----
                    with preview_tab:
                        st.code(mem["improved_code"], language=language, line_numbers=True)

                    # ---- AI review ----
                    with ai_tab:
                        st.caption("Uses Gemini to fix syntax issues, clean up formatting, and flag hardcoded secrets.")
                        if st.button("💡 Review with Gemini", key=f"review_{full_file_path}"):
                            try:
                                with st.spinner("Gemini is reviewing your code…"):
                                    agent = agent_graph()
                                    state = {
                                        "file_name": file_selected,
                                        "file_type": language,
                                        "file_content": mem["improved_code"],
                                    }
                                    result = agent.invoke(state, CONFIG)
                                mem["review_result"] = result
                            except ValueError as e:
                                st.error(str(e))

                        review_result = mem.get("review_result")
                        if review_result:
                            improved_code = review_result.get("improved_code")
                            corrections_summary = review_result.get("corrections_summary")

                            if improved_code and corrections_summary:
                                st.success("Gemini suggested an improved version.")

                                sub_tabs = st.tabs(["🆕 Improved code", "🔀 Diff", "🛠️ Summary"])
                                with sub_tabs[0]:
                                    st.code(improved_code, language=language, line_numbers=True)
                                with sub_tabs[1]:
                                    st.code(diff_view(mem["improved_code"], improved_code), language="diff")
                                with sub_tabs[2]:
                                    st.markdown(corrections_summary)

                                gemini_commit_msg = st.text_input(
                                    "Commit message for AI changes",
                                    "Apply Gemini code review suggestions",
                                    key=f"gemini_commit_{full_file_path}",
                                )
                                if st.button("✅ Commit AI changes", type="primary", key=f"gemini_commit_btn_{full_file_path}"):
                                    if not gemini_commit_msg.strip():
                                        st.error("Commit message cannot be empty.")
                                    else:
                                        _, latest_sha = get_file_content(repo_full_name, full_file_path)
                                        with st.spinner("Committing to GitHub…"):
                                            result = update_file(repo_full_name, full_file_path, improved_code, latest_sha, gemini_commit_msg)
                                        if result:
                                            st.success("File updated and committed.")
                                            mem["improved_code"] = improved_code
                                            mem["commit_message"] = gemini_commit_msg
                                            st.rerun()
                                        else:
                                            st.error("Failed to commit. Check the token's permissions.")
                            else:
                                st.error("Gemini couldn't produce an improved version for this file.")

    # ================= Upload =================
    with upload_tab:
        st.subheader("Upload a new file")
        st.caption(f"Will be added under `/{current_path}`" if current_path else "Will be added at the repository root.")

        uploaded_file = st.file_uploader("Choose a file", type=None)
        new_file_commit_msg = st.text_input(
            "Commit message", "Add new file via GithubAssist AI", key="upload_commit_msg"
        )

        if uploaded_file is not None:
            st.info(f"Ready to upload **{uploaded_file.name}** ({uploaded_file.size:,} bytes).")
            if st.button("🚀 Upload file", type="primary", disabled=not new_file_commit_msg.strip()):
                new_file_path = "/".join(st.session_state.path_stack + [uploaded_file.name])
                file_bytes = uploaded_file.read()
                with st.spinner("Uploading…"):
                    result = create_file(repo_full_name, new_file_path, file_bytes, new_file_commit_msg)
                if result:
                    st.success("File uploaded and committed.")
                    st.rerun()

    # ---------------- Debug / history ----------------
    with st.expander("🧠 Session history (debug)", expanded=False):
        st.json(st.session_state.gemini_memory)


if __name__ == "__main__":
    main()
