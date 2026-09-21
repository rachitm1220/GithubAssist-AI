# Maps file extensions to a display label, an emoji, and the language name
# `st.code`/Prettier/Black-style tooling expects for syntax highlighting.
EXTENSION_MAP = {
    ".py":   ("Python", "🐍", "python"),
    ".js":   ("JavaScript", "📜", "javascript"),
    ".jsx":  ("JavaScript (JSX)", "📜", "jsx"),
    ".ts":   ("TypeScript", "🟦", "typescript"),
    ".tsx":  ("TypeScript (TSX)", "🟦", "tsx"),
    ".java": ("Java", "☕", "java"),
    ".cpp":  ("C++", "💠", "cpp"),
    ".c":    ("C", "🔵", "c"),
    ".cs":   ("C#", "🎯", "csharp"),
    ".rb":   ("Ruby", "💎", "ruby"),
    ".go":   ("Go", "🐹", "go"),
    ".php":  ("PHP", "🐘", "php"),
    ".html": ("HTML", "🌐", "html"),
    ".css":  ("CSS", "🎨", "css"),
    ".json": ("JSON", "🧾", "json"),
    ".md":   ("Markdown", "📝", "markdown"),
    ".sh":   ("Shell Script", "💻", "bash"),
    ".yml":  ("YAML", "⚙️", "yaml"),
    ".yaml": ("YAML", "⚙️", "yaml"),
    ".rs":   ("Rust", "🦀", "rust"),
    ".swift": ("Swift", "🍎", "swift"),
    ".sql":  ("SQL", "🗄️", "sql"),
    ".xml":  ("XML", "📰", "xml"),
    ".toml": ("TOML", "⚙️", "toml"),
}


def detect_file_type(filename: str) -> str:
    """Backwards-compatible helper: returns 'emoji Label' as one string."""
    label, emoji, _ = _detect(filename)
    return f"{emoji} {label}"


def detect_file_type_details(filename: str):
    """Returns (label, emoji, language) for richer UI use (badges, code highlighting)."""
    return _detect(filename)


def _detect(filename: str):
    if filename.lower().startswith("readme"):
        return "README file", "📘", "markdown"

    lower = filename.lower()
    for ext, (label, emoji, lang) in EXTENSION_MAP.items():
        if lower.endswith(ext):
            return label, emoji, lang

    return "Unknown / Plain text", "📄", "text"
