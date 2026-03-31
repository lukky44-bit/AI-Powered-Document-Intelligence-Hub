from groq import Groq
from app.core.config import settings
from app.services.embedding_service import similarity_search
from app.agents.rag_agent import run_agentic_rag
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

    # ---------- 2️⃣ BUILD CONTEXT FOR AGENT INPUT ----------
    summary_section = ""
    if conversation_summary:
        summary_section = f"Conversation Summary:\n{conversation_summary}\n\n"

    recent_messages_text = _format_dialogue(recent_messages or [])
    if not recent_messages_text.strip():
        recent_messages_text = "(No recent messages)"

    # ---------- 3️⃣ EXECUTE AGENT (via app/agents/rag_agent.py) ----------
    try:
        agent_result = run_agentic_rag(
            query=query,
            top_k=top_k,
            file_id=file_id,
            allowed_file_ids=allowed_file_ids,
            summary_section=summary_section,
            recent_messages_text=recent_messages_text,
            mode_instruction=get_mode_instruction(mode),
            format_instruction=get_format_instruction(response_format),
        )

        answer = (agent_result.get("answer") or "").strip()
        source_type = str(agent_result.get("source_type") or "unknown")
        used_tools = set(agent_result.get("tools_used") or [])
        used_retriever = "document_retriever" in used_tools

        if answer:
            # Strict grounding: do not accept free-form model answers that used no tool.
            if not used_tools:
                answer = ""

        if answer:
            docs_for_response = docs
            if source_type in {"wikipedia", "web"} or not used_retriever:
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
                        "tools_used": sorted(used_tools | {"document_retriever"}),
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
