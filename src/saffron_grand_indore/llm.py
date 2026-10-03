from langchain_openai import ChatOpenAI
from .config import MODEL_NAME

llm = ChatOpenAI(model=MODEL_NAME)


def extract_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and "text" in part:
                parts.append(part["text"])
        return "".join(parts)
    return str(content)


def normalize_content(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and "text" in part:
                parts.append(part["text"])
        return "".join(parts)
    return str(content) if content is not None else ""


def safe_invoke(messages):
    try:
        response = llm.invoke(messages)
        return extract_text(response.content)
    except Exception as e:
        print(f"LLM call failed: {e}")
        return (
            "I'm having trouble responding right now — please try again in a moment. "
            "If this keeps happening, feel free to reach out to us directly on WhatsApp or Instagram."
        )