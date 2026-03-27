from groq import Groq
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
from app.services.embedding_service import get_ensemble_retriever, similarity_search
from typing import Any

client = Groq(api_key=settings.GROQ_API_KEY)


# ---------------------------------------------------------
# FORMAT INSTRUCTIONS
# ---------------------------------------------------------
def get_format_instruction(response_format: str):
    if response_format == "markdown":
        return (
            "Return the answer strictly in Markdown format. "
            "Use headings, bullet points, and emphasis where appropriate. "
            "Do NOT include explanations outside the formatted content."
        )

    if response_format == "json":
        return (
            "Return the answer strictly as valid JSON. "
            "Do NOT include any text outside the JSON object. "
            "Do NOT add markdown fences. "
            "Ensure keys are descriptive and values are concise."
        )

    if response_format == "table":
        return (
            "Return the answer strictly as a table. "
            "Use a Markdown table with clear column headers. "
            "Do NOT include explanations outside the table."
        )

    return "Return the answer as clear, concise plain text."


# ---------------------------------------------------------
# MODE INSTRUCTIONS
# ---------------------------------------------------------
def get_mode_instruction(mode: str):
    if mode == "legal":
        return (
            "You are a legal assistant. "
            "Use precise legal language. "
            "Refer explicitly to clauses where possible. "
            "Do not provide legal advice beyond the document content."
        )

    if mode == "finance":
        return (
            "You are a finance expert. "
            "Use financial terminology accurately. "
            "Avoid speculation or assumptions."
        )

    if mode == "academic":
        return (
            "You are an academic research assistant. "
            "Use formal and structured language. "
            "Base answers strictly on the provided content."
        )

    if mode == "healthcare":
        return (
            "You are a medical information assistant. "
            "Use neutral, factual medical language. "
            "Do NOT provide diagnosis or treatment advice. "
            "Include a brief disclaimer if relevant."
        )

    if mode == "business":
        return "You are a business analyst. Focus on actionable insights and summaries."

    return "You are an intelligent document assistant."


def _format_dialogue(messages: list[Any]) -> str:
    lines = []

    for msg in messages:
        role = getattr(msg, "role", None)
        content = getattr(msg, "content", None)

        if isinstance(msg, dict):
            role = msg.get("role")
            content = msg.get("content")

        if not content:
            continue

        role_label = (role or "message").upper()
        lines.append(f"{role_label}: {content}")

    return "\n".join(lines)


def summarize_messages(messages: list[Any]) -> str:
    dialogue = _format_dialogue(messages)
    if not dialogue.strip():
        return ""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "Summarize the following conversation briefly. "
                    "Capture the important context and topics discussed. "
                    "Keep it concise but informative."
                ),
            },
            {
                "role": "user",
                "content": dialogue,
            },
        ],
        temperature=0.1,
    )

    return response.choices[0].message.content.strip()


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


def _answer_from_documents(
    query: str,
    docs: list[dict[str, Any]],
    mode: str,
    response_format: str,
) -> str | None:
    if not docs:
        return None

    context_blocks = []
    for i, d in enumerate(docs, start=1):
        text = (d.get("text") or "").strip()
        if not text:
            continue
        context_blocks.append(f"[Source {i}]\n{text}")

    if not context_blocks:
        return None

    context = "\n\n".join(context_blocks)

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    f"{get_mode_instruction(mode)} "
                    "Answer using ONLY the provided retrieved document context. "
                    "Do NOT use external or internal knowledge. "
                    "If context is insufficient, clearly say the retrieved documents do not contain enough information."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Retrieved Context:\n{context}\n\n"
                    f"Question:\n{query}\n\n"
                    f"{get_format_instruction(response_format)}"
                ),
            },
        ],
        temperature=0.1,
    )

    text = (response.choices[0].message.content or "").strip()
    return text or None


def _build_agent_tools(
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
        """PRIMARY TOOL. Always call this tool first for every question.

        Use this to retrieve evidence from uploaded documents before using any external source.
        If it returns no useful evidence, then consider `wikipedia_lookup` for concepts/definitions,
        or `duckduckgo_web_search` for explicit web/current-events requests.
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
        """Use this for encyclopedic definitions, background concepts, and factual explainers.

        Best for "what is", "define", historical/scientific concepts, and broad knowledge questions.
        Prefer `document_retriever` first, then use this when document context is insufficient.
        """
        wiki_text = (wikipedia_api.run(search_query) or "").strip()
        return wiki_text if wiki_text else "NO_WIKIPEDIA_RESULT"

    tools.append(wikipedia_lookup)

    duckduckgo_api = DuckDuckGoSearchAPIWrapper(max_results=5)
    duckduckgo_run = DuckDuckGoSearchRun(api_wrapper=duckduckgo_api)

    @tool("duckduckgo_web_search")
    def duckduckgo_web_search(search_query: str) -> str:
        """Use this for explicit web lookups, recent events, live updates, or internet-wide information.

        Trigger this when the user asks for latest/current/news/trending data or specifically asks to search the web.
        Keep `document_retriever` as first priority for normal document-grounded QA.
        """
        web_text = duckduckgo_run.run(search_query)
        text = web_text.strip() if isinstance(web_text, str) else str(web_text).strip()
        return text if text else "NO_WEB_RESULT"

    tools.append(duckduckgo_web_search)

    return tools


# ---------------------------------------------------------
# CONVERSATIONAL RAG FUNCTION
# ---------------------------------------------------------
def generate_rag_answer(
    query: str,
    top_k: int = 15,
    file_id: str = None,
    allowed_file_ids: list[str] | None = None,
    mode: str = "general",
    response_format: str = "text",
    conversation_summary: str | None = None,
    recent_messages: list[Any] | None = None,
    include_source_details: bool = False,
):
    # ---------- 1️⃣ RETRIEVAL FOR SOURCE ATTRIBUTION ----------
    docs = similarity_search(
        query=query,
        top_k=top_k,
        file_id=file_id,
        file_ids=None if file_id else allowed_file_ids,
    )

    # ---------- 2️⃣ BUILD AGENT TOOLS ----------
    tools = _build_agent_tools(
        top_k=top_k,
        file_id=file_id,
        allowed_file_ids=allowed_file_ids,
    )

    if not tools:
        if include_source_details:
            return (
                "No tools available to answer the question.",
                [],
                {"source_type": "none", "tools_used": []},
            )
        return "No tools available to answer the question.", []

    # ---------- 3️⃣ BUILD CONTEXT FOR AGENT INPUT ----------
    summary_section = ""
    if conversation_summary:
        summary_section = f"Conversation Summary:\n{conversation_summary}\n\n"

    recent_messages_text = _format_dialogue(recent_messages or [])
    if not recent_messages_text.strip():
        recent_messages_text = "(No recent messages)"

    agent_input = f"""
{summary_section}Recent Messages:
{recent_messages_text}

User Question:
{query}

Output formatting requirement:
{get_format_instruction(response_format)}
"""

    # ---------- 4️⃣ BUILD AGENT ----------
    llm = ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model="llama-3.3-70b-versatile",
        temperature=0.1,
    )

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=(
            f"{get_mode_instruction(mode)} "
            "You are an agentic assistant with tools: "
            "`document_retriever`, `wikipedia_lookup`, and `duckduckgo_web_search`. "
            "Always call `document_retriever` first. "
            "Use `wikipedia_lookup` for definitions and background concepts. "
            "Use `duckduckgo_web_search` only when the user explicitly needs web/current-events information. "
            "Prefer uploaded document evidence when available. "
            "After tool usage, generate the final response clearly and concisely."
        ),
    )

    # ---------- 5️⃣ EXECUTE AGENT ----------
    try:
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

        if answer:
            # Strict grounding: do not accept free-form model answers that used no tool.
            if not used_tools:
                answer = ""

        if answer:
            docs_for_response = docs
            if source_type in {"wikipedia", "web"}:
                docs_for_response = []

            if include_source_details:
                return (
                    answer,
                    docs_for_response,
                    {
                        "source_type": source_type,
                        "tools_used": sorted(used_tools),
                    },
                )
            return answer, docs_for_response

        # Agent did not produce a usable grounded answer.
        # Fall back to retriever-grounded synthesis (documents only, no external fallback).
        grounded_fallback = _answer_from_documents(
            query=query,
            docs=docs,
            mode=mode,
            response_format=response_format,
        )
        if grounded_fallback:
            if include_source_details:
                return (
                    grounded_fallback,
                    docs,
                    {
                        "source_type": "documents",
                        "tools_used": sorted(set(used_tools) | {"document_retriever"}),
                    },
                )
            return grounded_fallback, docs
    except Exception:
        grounded_fallback = _answer_from_documents(
            query=query,
            docs=docs,
            mode=mode,
            response_format=response_format,
        )
        if grounded_fallback:
            if include_source_details:
                return (
                    grounded_fallback,
                    docs,
                    {
                        "source_type": "documents",
                        "tools_used": ["document_retriever"],
                    },
                )
            return grounded_fallback, docs

    if include_source_details:
        return (
            "I couldn't generate a grounded answer from available tools.",
            [],
            {
                "source_type": "none",
                "tools_used": [],
            },
        )
    return "I couldn't generate a grounded answer from available tools.", []
