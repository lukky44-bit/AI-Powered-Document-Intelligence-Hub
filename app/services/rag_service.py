from groq import Groq
from langchain.agents import create_agent
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import create_retriever_tool
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
        if isinstance(msg, ToolMessage):
            tool_name = getattr(msg, "name", None)
            if tool_name:
                used_tools.add(str(tool_name))

    return used_tools


def _is_no_info_answer(answer: str) -> bool:
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


def _answer_from_wikipedia(
    query: str,
    mode: str,
    response_format: str,
    wikipedia_tool: WikipediaQueryRun,
):
    wiki_text = wikipedia_tool.run(query).strip()
    if not wiki_text:
        return None

    wiki_response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    f"{get_mode_instruction(mode)} Use the Wikipedia context to answer."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Wikipedia Result:\n{wiki_text}\n\n"
                    f"User Question:\n{query}\n\n"
                    f"{get_format_instruction(response_format)}"
                ),
            },
        ],
        temperature=0.1,
    )
    return wiki_response.choices[0].message.content.strip()


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

        if answer:
            # Strict grounding: do not accept free-form model answers that used no tool.
            if not used_tools:
                answer = ""

        if answer:
            if _is_no_info_answer(answer):
                wiki_answer = _answer_from_wikipedia(
                    query=query,
                    mode=mode,
                    response_format=response_format,
                    wikipedia_tool=wikipedia_tool,
                )
                if wiki_answer:
                    if include_source_details:
                        return (
                            wiki_answer,
                            [],
                            {
                                "source_type": "wikipedia",
                                "tools_used": sorted(set(used_tools) | {"wikipedia"}),
                            },
                        )
                    return wiki_answer, []

            docs_for_response = docs
            if source_type == "wikipedia":
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
    except Exception:
        pass

    # ---------- 6️⃣ SAFE FALLBACK ----------
    if docs:
        context_blocks = []
        for i, d in enumerate(docs):
            context_blocks.append(f"[Source {i + 1}]\n{d['text']}")

        context = "\n\n".join(context_blocks)

        fallback_response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"{get_mode_instruction(mode)} "
                        "Answer using ONLY the provided document context. "
                        "Do NOT use your internal knowledge. "
                        "If context is insufficient, reply EXACTLY with: INSUFFICIENT_DOCUMENT_CONTEXT"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Relevant Documents:\n{context}\n\n"
                        f"Question:\n{query}\n\n"
                        f"{get_format_instruction(response_format)}"
                    ),
                },
            ],
            temperature=0.1,
        )
        fallback_answer = fallback_response.choices[0].message.content.strip()

        if _is_no_info_answer(fallback_answer):
            wiki_answer = _answer_from_wikipedia(
                query=query,
                mode=mode,
                response_format=response_format,
                wikipedia_tool=wikipedia_tool,
            )
            if wiki_answer:
                if include_source_details:
                    return (
                        wiki_answer,
                        [],
                        {
                            "source_type": "wikipedia",
                            "tools_used": ["wikipedia"],
                        },
                    )
                return wiki_answer, []

        if include_source_details:
            return (
                fallback_answer,
                docs,
                {
                    "source_type": "documents",
                    "tools_used": ["document_retriever"],
                },
            )
        return fallback_answer, docs

    wiki_answer = _answer_from_wikipedia(
        query=query,
        mode=mode,
        response_format=response_format,
        wikipedia_tool=wikipedia_tool,
    )
    if not wiki_answer:
        if include_source_details:
            return (
                "No relevant information found in documents or Wikipedia.",
                [],
                {"source_type": "none", "tools_used": []},
            )
        return "No relevant information found in documents or Wikipedia.", []
    if include_source_details:
        return (
            wiki_answer,
            [],
            {
                "source_type": "wikipedia",
                "tools_used": ["wikipedia"],
            },
        )
    return wiki_answer, []
