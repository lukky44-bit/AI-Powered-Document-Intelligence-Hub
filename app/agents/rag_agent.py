from typing import Any

from groq import Groq
from langchain.agents import create_agent
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import create_retriever_tool
from langchain_groq import ChatGroq

from app.core.config import settings
from app.services.embedding_service import get_ensemble_retriever


def _extract_tool_names(messages: list[Any] | None) -> set[str]:
    used_tools: set[str] = set()
    if not messages:
        return used_tools

    for msg in messages:
        if isinstance(msg, ToolMessage):
            tool_name = getattr(msg, "name", None)
            if tool_name:
                used_tools.add(str(tool_name))

    return used_tools


def _build_agent_input(
    query: str,
    format_instruction: str,
    summary_section: str,
    recent_messages_text: str,
) -> str:
    return f"""
{summary_section}Recent Messages:
{recent_messages_text}

User Question:
{query}

Output formatting requirement:
{format_instruction}
"""


def is_no_info_answer(answer: str) -> bool:
    text = (answer or "").strip().lower()
    if not text:
        return True

    no_info_signals = [
        "the document does not contain this information",
        "does not contain this information",
        "not available in the provided context",
        "not enough information",
        "insufficient information",
        "insufficient_document_context",
    ]

    return any(signal in text for signal in no_info_signals)


def answer_from_wikipedia(
    query: str,
    mode_instruction: str,
    format_instruction: str,
    wikipedia_tool: WikipediaQueryRun,
    client: Groq,
):
    wiki_text = wikipedia_tool.run(query).strip()
    if not wiki_text:
        return None

    wiki_response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": f"{mode_instruction} Use the Wikipedia context to answer.",
            },
            {
                "role": "user",
                "content": (
                    f"Wikipedia Result:\n{wiki_text}\n\n"
                    f"User Question:\n{query}\n\n"
                    f"{format_instruction}"
                ),
            },
        ],
        temperature=0.1,
    )
    return wiki_response.choices[0].message.content.strip()


def run_agentic_rag(
    query: str,
    top_k: int,
    file_id: str | None,
    allowed_file_ids: list[str] | None,
    summary_section: str,
    recent_messages_text: str,
    mode_instruction: str,
    format_instruction: str,
) -> dict[str, Any]:
    tools = []

    ensemble_retriever = get_ensemble_retriever(
        top_k=top_k,
        file_id=file_id,
        file_ids=None if file_id else allowed_file_ids,
    )

    if ensemble_retriever:
        tools.append(
            create_retriever_tool(
                retriever=ensemble_retriever,
                name="document_retriever",
                description=(
                    "Search uploaded documents for relevant passages. "
                    "Use this FIRST for every question."
                ),
            )
        )

    wikipedia_tool = WikipediaQueryRun(
        api_wrapper=WikipediaAPIWrapper(top_k_results=3, doc_content_chars_max=3000)
    )
    tools.append(wikipedia_tool)

    if not tools:
        return {
            "answer": None,
            "source_type": "none",
            "tools_used": [],
            "wikipedia_tool": None,
            "ok": False,
        }

    agent_input = _build_agent_input(
        query=query,
        format_instruction=format_instruction,
        summary_section=summary_section,
        recent_messages_text=recent_messages_text,
    )

    llm = ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model="llama-3.3-70b-versatile",
        temperature=0.1,
    )

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=(
            f"{mode_instruction} "
            "You are an agentic assistant with two tools: "
            "`document_retriever` and `wikipedia`. "
            "Always call `document_retriever` first. "
            "If document retrieval returns empty or irrelevant results, "
            "then call `wikipedia`. "
            "Never reply with 'The document does not contain this information.' "
            "If document evidence is insufficient, you must use `wikipedia` before finalizing. "
            "Prefer uploaded document evidence when available. "
            "After tool usage, generate the final response clearly and concisely."
        ),
    )

    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": agent_input,
                }
            ]
        }
    )

    answer = ""
    source_type = "unknown"
    messages = result.get("messages") if isinstance(result, dict) else None
    used_tools = _extract_tool_names(messages)
    used_retriever = "document_retriever" in used_tools
    used_wikipedia = "wikipedia" in used_tools

    if used_retriever and used_wikipedia:
        source_type = "documents_and_wikipedia"
    elif used_retriever:
        source_type = "documents"
    elif used_wikipedia:
        source_type = "wikipedia"

    if messages:
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and isinstance(msg.content, str):
                answer = msg.content.strip()
                if answer:
                    break

    if answer and not used_tools:
        answer = ""

    return {
        "answer": answer,
        "source_type": source_type,
        "tools_used": sorted(used_tools),
        "wikipedia_tool": wikipedia_tool,
        "ok": True,
    }
