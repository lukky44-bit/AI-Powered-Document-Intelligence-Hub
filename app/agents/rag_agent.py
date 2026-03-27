from typing import Any

from langchain.agents import create_agent
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.utilities import (
    DuckDuckGoSearchAPIWrapper,
    WikipediaAPIWrapper,
)
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq

from app.core.config import settings
from app.services.embedding_service import get_ensemble_retriever


def _extract_tool_names(messages: list[Any] | None) -> set[str]:
    used_tools: set[str] = set()
    if not messages:
        return used_tools

    for msg in messages:
        tool_calls = getattr(msg, "tool_calls", None)
        if isinstance(tool_calls, list):
            for call in tool_calls:
                if isinstance(call, dict):
                    name = call.get("name")
                    if name:
                        used_tools.add(str(name))

        if isinstance(msg, ToolMessage):
            tool_name = getattr(msg, "name", None)
            if tool_name:
                used_tools.add(str(tool_name))

        if isinstance(msg, dict):
            role = str(msg.get("role", "")).lower()
            msg_type = str(msg.get("type", "")).lower()
            tool_name = msg.get("name")
            if tool_name and (role == "tool" or msg_type in {"tool", "toolmessage"}):
                used_tools.add(str(tool_name))

            dict_tool_calls = msg.get("tool_calls")
            if isinstance(dict_tool_calls, list):
                for call in dict_tool_calls:
                    if isinstance(call, dict):
                        name = call.get("name")
                        if name:
                            used_tools.add(str(name))

    return used_tools


def _extract_text_content(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                text = item.strip()
                if text:
                    parts.append(text)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content") or item.get("output")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
        return "\n".join(parts).strip()

    return ""


def _extract_final_answer(messages: list[Any] | None) -> str:
    if not messages:
        return ""

    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            text = _extract_text_content(getattr(msg, "content", ""))
            if text:
                return text

        if isinstance(msg, dict):
            role = str(msg.get("role", "")).lower()
            msg_type = str(msg.get("type", "")).lower()
            if role in {"assistant", "ai"} or msg_type in {"ai", "assistant"}:
                text = _extract_text_content(msg.get("content"))
                if text:
                    return text

    return ""


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


def _build_tools(
    top_k: int,
    file_id: str | None,
    allowed_file_ids: list[str] | None,
):
    tools = []

    ensemble_retriever = get_ensemble_retriever(
        top_k=top_k,
        file_id=file_id,
        file_ids=None if file_id else allowed_file_ids,
    )

    @tool("document_retriever")
    def document_retriever(search_query: str) -> str:
        """PRIMARY TOOL. Always call this first for every user query.

        Retrieves evidence from uploaded files. Prefer this tool for default RAG behavior.
        If no useful document context is found, then use `wikipedia_lookup` for definitions/concepts
        or `duckduckgo_web_search` for explicit web/current-events queries.
        """
        if not ensemble_retriever:
            return "NO_DOCUMENT_CONTEXT_FOUND"

        retrieved_docs = ensemble_retriever.invoke(search_query)
        if not retrieved_docs:
            return "NO_DOCUMENT_CONTEXT_FOUND"

        chunks = []
        for idx, doc in enumerate(retrieved_docs, start=1):
            text = (getattr(doc, "page_content", "") or "").strip()
            metadata = getattr(doc, "metadata", {}) or {}
            source = metadata.get("source", "unknown")
            page = metadata.get("page")
            page_label = f", page={page}" if page is not None else ""
            if text:
                chunks.append(f"[{idx}] source={source}{page_label}\n{text}")

        return "\n\n".join(chunks) if chunks else "NO_DOCUMENT_CONTEXT_FOUND"

    tools.append(document_retriever)

    wikipedia_api = WikipediaAPIWrapper(top_k_results=3, doc_content_chars_max=3000)

    @tool("wikipedia_lookup")
    def wikipedia_lookup(search_query: str) -> str:
        """Use for definitions, background concepts, and encyclopedic explanations.

        Use this when the user asks "what is", "define", or needs broad concept grounding.
        Keep `document_retriever` as the first step in standard RAG flows.
        """
        wiki_text = (wikipedia_api.run(search_query) or "").strip()
        return wiki_text if wiki_text else "NO_WIKIPEDIA_RESULT"

    tools.append(wikipedia_lookup)

    duckduckgo_api = DuckDuckGoSearchAPIWrapper(max_results=5)
    duckduckgo_run = DuckDuckGoSearchRun(api_wrapper=duckduckgo_api)

    @tool("duckduckgo_web_search")
    def duckduckgo_web_search(search_query: str) -> str:
        """Use for explicit web search needs, latest updates, and current event queries.

        If the user asks for recent/live internet information, use this tool.
        Otherwise, prioritize `document_retriever` for document-grounded answers.
        """
        web_text = duckduckgo_run.run(search_query)
        text = web_text.strip() if isinstance(web_text, str) else str(web_text).strip()
        return text if text else "NO_WEB_RESULT"

    tools.append(duckduckgo_web_search)

    return tools


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
    tools = _build_tools(
        top_k=top_k,
        file_id=file_id,
        allowed_file_ids=allowed_file_ids,
    )

    if not tools:
        return {
            "answer": None,
            "source_type": "none",
            "tools_used": [],
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
            "You are an agentic assistant with tools: "
            "`document_retriever`, `wikipedia_lookup`, and `duckduckgo_web_search`. "
            "Always call `document_retriever` first. "
            "Use `wikipedia_lookup` for definitions/background concepts. "
            "Use `duckduckgo_web_search` only for explicit web/current-events requests. "
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
    used_wikipedia = "wikipedia_lookup" in used_tools
    used_web = "duckduckgo_web_search" in used_tools

    if used_retriever and (used_wikipedia or used_web):
        source_type = "documents_plus_external"
    elif used_retriever:
        source_type = "documents"
    elif used_web:
        source_type = "web"
    elif used_wikipedia:
        source_type = "wikipedia"

    answer = _extract_final_answer(messages)

    if answer and not used_tools:
        answer = ""

    return {
        "answer": answer,
        "source_type": source_type,
        "tools_used": sorted(used_tools),
        "ok": True,
    }
