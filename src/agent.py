import os
import re
import streamlit as st

from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, SystemMessage
from typing import TypedDict, Optional


def _resolve_gemini_key() -> Optional[str]:
    """
    Resolve the Gemini API key from (in order of priority):
    1. st.session_state (set via the sidebar in app.py)
    2. st.secrets["GOOGLE_API_KEY"]  (for deployed / Streamlit Cloud usage)
    3. the GOOGLE_API_KEY environment variable
    """
    key = st.session_state.get("google_api_key")
    if key:
        return key
    try:
        if "GOOGLE_API_KEY" in st.secrets:
            return st.secrets["GOOGLE_API_KEY"]
    except Exception:
        pass
    return os.environ.get("GOOGLE_API_KEY")


def get_llm():
    """Lazily build the Gemini chat model once a key is available."""
    api_key = _resolve_gemini_key()
    if not api_key:
        raise ValueError(
            "No Gemini API key found. Add it in the sidebar, or set GOOGLE_API_KEY "
            "as an environment variable / Streamlit secret."
        )
    os.environ["GOOGLE_API_KEY"] = api_key
    return init_chat_model("google_genai:gemini-2.5-flash", temperature=0)

def extract_code_only(output: str) -> str:
    """
    Extracts and returns only the raw code from the LLM response.
    Removes markdown backticks and any leading explanations or comments.
    """
    # Remove markdown code block formatting
    output = re.sub(r"^```[a-zA-Z]*\n?", "", output)
    output = re.sub(r"\n?```$", "", output)

    # Remove lines that look like explanations or bullet points
    lines = output.splitlines()
    code_lines = []
    for line in lines:
        # Skip lines that look like markdown bullets, summaries, or doc-style comments
        if line.strip().startswith(("*", "#", "By ", "**", "//", "Fixes and", "Further Suggestions", "```")):
            continue
        code_lines.append(line)

    return "\n".join(code_lines).strip()


# ---- State Type for LangGraph ----
# Type for state
class CodeImproveState(TypedDict):
    file_name: str
    file_type: str
    file_content: str
    improved_code: Optional[str]
    corrections_summary: Optional[str]

def detect_and_convert_code_language(state: CodeImproveState, llm) -> CodeImproveState:
    """
    Detect the language of the current code and convert it into the correct language
    based on the file type provided in the state.
    """
    # Request to detect language
    detect_language_prompt = SystemMessage(content=f"""
    Identify the programming language of the following code:

    {state['file_content']}
    """)

    # Use the Gemini model to detect the code's programming language
    response_language = llm.invoke([detect_language_prompt, HumanMessage(content=state['file_content'])])
    detected_language = response_language.content.strip()

    # Check if the detected language matches the file type
    if detected_language != state['file_type']:
        # Request to translate the code into the correct programming language
        translate_prompt = SystemMessage(content=f"""
        Translate the following code from {detected_language} to {state['file_type']}:

        {state['file_content']}
        """)

        # Invoke model to translate the code
        response_translation = llm.invoke([translate_prompt, HumanMessage(content=state['file_content'])])
        state['file_content'] = response_translation.content  # Update the content with the translated code

    return state

def improve_code_node(state: CodeImproveState) -> CodeImproveState:
    llm = get_llm()

    # Step 1: Detect and convert the code language if needed
    state = detect_and_convert_code_language(state, llm)

    prompt_code = SystemMessage(content=f"""
    You are a code improvement assistant.

    Analyze the following code which may contain syntax errors, missing arguments, or poor formatting.

    Tasks:
    1. Fix any syntax or indentation errors.
    2. Provide a corrected and working version.
    3. Don't add or remove any comments.
    4. Remove any hardcoded secrets or unsafe code.

    Return ONLY the corrected code, without any explanation, comments, or summary. 
    Do NOT include a description of changes. 
    Do NOT wrap the code in triple backticks or markdown formatting.
    Your response must be a standalone code block only. 

    File Name: {state['file_name']}
    File Type: {state['file_type']}
    """)

    response_improved = llm.invoke([prompt_code, HumanMessage(content=state['file_content'])])
    raw_output = response_improved.content
    cleaned_code = extract_code_only(raw_output)
    state['improved_code'] = cleaned_code


    prompt_errors = SystemMessage(content=""" 
    You have improved the code. Please provide a brief summary of the changes made.
    Focus on logic fixes, formatting, sensitive data removed, etc.
    """)

    response_summary = llm.invoke([prompt_errors, HumanMessage(content=f"Original Code:\n{state['file_content']}\n\nImproved Code:\n{state['improved_code']}")])
    state['corrections_summary'] = response_summary.content  # <-- access .content

    return state

def agent_graph():
    graph = StateGraph(CodeImproveState)
    graph.add_node("agent", improve_code_node)
    graph.set_entry_point("agent")
    graph.set_finish_point("agent")

    memory = MemorySaver()
    return graph.compile(checkpointer=memory)
