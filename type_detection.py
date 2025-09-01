import streamlit as st
import requests
import base64

def detect_file_type(filename):
    if filename.lower().startswith("readme"):
        return "📘 README file"
    
    extension_to_language = {
        ".py": "🐍 Python",
        ".js": "📜 JavaScript",
        ".ts": "🟦 TypeScript",
        ".java": "☕ Java",
        ".cpp": "💠 C++",
        ".c": "🔵 C",
        ".cs": "🎯 C#",
        ".rb": "💎 Ruby",
        ".go": "🐹 Go",
        ".php": "🐘 PHP",
        ".html": "🌐 HTML",
        ".css": "🎨 CSS",
        ".json": "🧾 JSON",
        ".md": "📝 Markdown",
        ".sh": "💻 Shell Script",
        ".yml": "⚙️ YAML",
        ".yaml": "⚙️ YAML",
        ".rs": "🦀 Rust",
        ".swift": "🍎 Swift"
    }

    for ext, lang in extension_to_language.items():
        if filename.lower().endswith(ext):
            return lang
    return "📄 Unknown / Plain text"
