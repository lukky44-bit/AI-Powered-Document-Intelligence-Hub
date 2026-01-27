from groq import Groq
from app.services.embedding_service import similarity_search
from app.core.config import settings

client = Groq(api_key=settings.GROQ_API_KEY)


def get_prompt_by_mode(mode: str, context: str, query: str):
    if mode == "legal":
        system = "You are a legal assistant. Answer using formal legal language and cite clauses if possible."
    elif mode == "finance":
        system = "You are a finance expert. Answer clearly with financial terminology and risk awareness."
    elif mode == "academic":
        system = "You are an academic research assistant. Use formal tone and structured explanations."
    elif mode == "healthcare":
        system = "You are a medical assistant. Answer carefully and add disclaimers where necessary."
    elif mode == "business":
        system = (
            "You are a business analyst. Focus on actionable insights and summaries."
        )

    else:
        system = "You are an intelligent document assistant."

    user_prompt = f"""
Use the following context to answer the question.

Context:
{context}

Question:
{query}

Answer clearly and only using the context.
"""
    return system, user_prompt


def generate_rag_answer(
    query: str, top_k: int = 3, file_id: str = None, mode: str = "general"
):
    docs = similarity_search(query, top_k, file_id)

    context = ""
    for i, d in enumerate(docs):
        context += f"Chunk {i + 1}:\n{d['text']}\n\n"

    system_prompt, user_prompt = get_prompt_by_mode(mode, context, query)

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )

    answer = response.choices[0].message.content
    return answer, docs
