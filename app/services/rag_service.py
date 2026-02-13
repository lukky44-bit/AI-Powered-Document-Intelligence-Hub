from groq import Groq
from app.core.config import settings
from app.services.embedding_service import similarity_search

client = Groq(api_key=settings.GROQ_API_KEY)


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


def generate_rag_answer(
    query: str,
    top_k: int = 15,
    file_id: str = None,
    mode: str = "general",
    response_format: str = "text",
):
    # ---------- RETRIEVAL ----------
    docs = similarity_search(query, top_k, file_id)

    if not docs:
        return "No relevant information found in the documents.", []

    # ---------- CONTEXT ----------
    context_blocks = []
    for i, d in enumerate(docs):
        context_blocks.append(f"[Source {i + 1}]\n{d['text']}")

    context = "\n\n".join(context_blocks)

    # ---------- PROMPTS ----------
    system_prompt = (
        f"{get_mode_instruction(mode)} "
        "You must answer using ONLY the provided context. "
        "If the answer is not present in the context, say "
        "'The document does not contain this information.'"
    )

    user_prompt = f"""
Context:
{context}

Question:
{query}

Response requirements:
{get_format_instruction(response_format)}
"""

    # ---------- LLM CALL ----------
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
    )

    answer = response.choices[0].message.content.strip()
    return answer, docs
