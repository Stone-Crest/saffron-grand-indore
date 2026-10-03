import re
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from .retrieval import retrieve_with_confidence
from .llm import safe_invoke, normalize_content
from .calculator import compute_stay_cost
from .prompts import SYSTEM_PROMPT_TEMPLATE
from .config import MAX_HISTORY_MESSAGES

SOURCES_LINE_PATTERN = re.compile(r"\n\n_Sources:.*_$", re.DOTALL)


def strip_sources_line(text):
    return SOURCES_LINE_PATTERN.sub("", text or "")


def history_to_messages(history):
    messages = []
    if not history:
        return messages
    for turn in history:
        if isinstance(turn, dict):
            role = turn.get("role")
            content = normalize_content(turn.get("content", ""))
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=strip_sources_line(content)))
        elif isinstance(turn, (list, tuple)) and len(turn) == 2:
            user_msg, assistant_msg = turn
            if user_msg:
                messages.append(HumanMessage(content=normalize_content(user_msg)))
            if assistant_msg:
                messages.append(AIMessage(content=strip_sources_line(normalize_content(assistant_msg))))
    return messages[-MAX_HISTORY_MESSAGES:]


def answer_question(question, history):
    docs, relevant_types = retrieve_with_confidence(question)
    past_messages = history_to_messages(history)

    history_text = " ".join(
        normalize_content(turn.get("content", ""))
        for turn in (history or [])
        if isinstance(turn, dict)
    )

    if not docs:
        return safe_invoke([
            SystemMessage(content=(
                "You are the virtual concierge for The Saffron Grand, a luxury 5-star hotel "
                "in Vijay Nagar, Indore. No specific hotel information was found for this message. "
                "If it's small talk or a greeting, respond warmly and invite the guest to ask about "
                "rooms, dining, spa services, facilities, policies, location, parking, or contact details. "
                "If it's a factual question, say you don't have that information and suggest they contact "
                "the hotel directly using the details you have, or ask about something else."
            )),
            *past_messages,
            HumanMessage(content=question),
        ])

    context = "\n\n".join(doc.page_content for doc in docs)
    computed_check = compute_stay_cost(question, history_text)
    if computed_check:
        context = f"{context}\n\n{computed_check}"

    formatted_prompt = SYSTEM_PROMPT_TEMPLATE.format(context=context)
    return safe_invoke([
        SystemMessage(content=formatted_prompt),
        *past_messages,
        HumanMessage(content=question),
    ])