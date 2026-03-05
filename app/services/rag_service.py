from groq import Groq
from app.core.config import settings
from app.services.embedding_service import similarity_search
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
):
    # ---------- 1️⃣ RETRIEVAL ----------
    docs = similarity_search(
        query=query,
        top_k=top_k,
        file_id=file_id,
        file_ids=None if file_id else allowed_file_ids,
    )

    if not docs:
        return "No relevant information found in the documents.", []

    # ---------- 2️⃣ BUILD CONTEXT ----------
    context_blocks = []
    for i, d in enumerate(docs):
        context_blocks.append(f"[Source {i + 1}]\n{d['text']}")

    context = "\n\n".join(context_blocks)

    # ---------- 3️⃣ BUILD MESSAGE LIST ----------
    messages = []

    # System prompt (mode + safety)
    system_prompt = (
        f"{get_mode_instruction(mode)} "
        "You must answer using ONLY the provided context. "
        "If the answer is not present in the context, say "
        "'The document does not contain this information.'"
    )

    messages.append(
        {
            "role": "system",
            "content": system_prompt,
        }
    )

    # ---------- 4️⃣ BUILD SUMMARY + RECENT CONTEXT ----------
    summary_section = ""
    if conversation_summary:
        summary_section = f"Conversation Summary:\n{conversation_summary}\n\n"

    recent_messages_text = _format_dialogue(recent_messages or [])
    if not recent_messages_text.strip():
        recent_messages_text = "(No recent messages)"

    # ---------- 5️⃣ ADD CURRENT QUESTION ----------
    final_user_prompt = f"""
{summary_section}Recent Messages:
{recent_messages_text}

Relevant Documents:
{context}

User Question:
{query}

Response requirements:
{get_format_instruction(response_format)}
"""

    messages.append(
        {
            "role": "user",
            "content": final_user_prompt,
        }
    )

    # ---------- 6️⃣ LLM CALL ----------
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.1,
    )

    answer = response.choices[0].message.content.strip()

    return answer, docs
