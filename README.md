# 🤖 GithubAssist AI

A Streamlit app for browsing, editing, and AI-reviewing files in your GitHub repositories — all from the browser, with no local clone required.

Connect a GitHub Personal Access Token, pick a repo, and you can view and edit files, auto-format code before committing, rename files/folders, upload new files, and run an AI code review (powered by Gemini + LangGraph) that fixes syntax issues, cleans up formatting, and flags hardcoded secrets.

## ✨ Features

- **Repo browser** — navigate folders with breadcrumbs, view files with syntax-highlighted previews
- **In-browser editing** — edit a file's content and commit straight back to GitHub
- **Auto-formatting** — Python via [Black](https://github.com/psf/black), JS/HTML/CSS via [Prettier](https://prettier.io/), applied before commit
- **AI code review** — Gemini reviews the current file, returns a corrected version plus a diff and a plain-language summary of what changed
- **Rename** files and folders (folder rename recursively renames every file inside)
- **Upload** new files into the current folder
- Session history of every AI review, viewable for debugging

## 🧱 Project structure

```
.
├── app.py                          # Streamlit UI and app flow
├── agent.py                        # LangGraph agent that drives the Gemini code review
├── authorization_file_content.py   # GitHub auth + repo/content/file API calls
├── upload_file.py                  # Create/upload a new file to a repo
├── rename_files.py                 # Rename/delete files and folders (copy + delete)
├── type_detection.py               # Maps file extensions to labels/emoji/language
├── requirements.txt
└── .gitignore
```

## 🚀 Getting started

### 1. Clone and install

```bash
git clone https://github.com/<your-username>/GithubAssist-AI.git
cd GithubAssist-AI
python -m venv venv
source venv/bin/activate   # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Prettier is optional and only needed for JS/HTML/CSS auto-formatting:

```bash
npm install -g prettier
```

### 2. Get a GitHub token

Create a [Personal Access Token](https://github.com/settings/tokens) with the **`repo`** scope (needed to read and write to private repositories). You'll paste this into the sidebar when the app runs — it's kept only in your browser session, never written to disk.

### 3. (Optional) Get a Gemini API key

The AI review feature needs a [Gemini API key](https://aistudio.google.com/app/apikey). You can provide it any of three ways:

- Paste it into the sidebar at runtime (simplest, session-only)
- Set it as an environment variable: `export GOOGLE_API_KEY=your-key`
- Add it to `.streamlit/secrets.toml` for a deployed app:
  ```toml
  GOOGLE_API_KEY = "your-key"
  ```

### 4. Run it

```bash
streamlit run app.py
```

Open the URL Streamlit prints (typically `http://localhost:8501`), enter your GitHub token in the sidebar, and pick a repository.

## 🖱️ Using the app

1. **Enter your GitHub token** in the sidebar. Repositories you have access to load automatically.
2. **Pick a repository**, then browse folders in the left panel of the *Browse & Edit* tab.
3. **Select a file** to open it in the *Edit*, *Preview*, or *AI Review* tabs on the right.
   - *Edit* — change the content directly and commit, with optional auto-formatting.
   - *Preview* — read-only, syntax-highlighted view of the current content.
   - *AI Review* — run Gemini on the file; review the diff and summary, then commit if you're happy with it.
4. **Rename** files or folders from the *Rename* panel under the file browser.
5. **Upload** a new file from the *Upload* tab — it lands in whichever folder you're currently browsing.

## ⚠️ Notes & limitations

- Renaming is implemented as *copy to new path, then delete old path* — this creates two separate commits and isn't atomic. Avoid renaming while other changes to the same file are in flight.
- Only text files can be viewed/edited in the browser; binary files (images, archives, etc.) can still be uploaded but not previewed or edited.
- The GitHub Contents API used here isn't ideal for very large files (typically >1MB) — GitHub imposes API size limits.
- Your GitHub token and Gemini key are kept only in Streamlit's session state; they are not persisted anywhere by this app.

## 🛠️ Tech stack

- [Streamlit](https://streamlit.io/) — UI
- [GitHub REST API](https://docs.github.com/en/rest) — repo/file operations
- [LangChain](https://www.langchain.com/) + [LangGraph](https://www.langchain.com/langgraph) — orchestrates the review agent
- [Gemini](https://ai.google.dev/) (`gemini-2.5-flash`) — the model behind the AI review
- [Black](https://github.com/psf/black) / [Prettier](https://prettier.io/) — code formatting

## 📄 License

Add a license of your choice (e.g. MIT) here.
