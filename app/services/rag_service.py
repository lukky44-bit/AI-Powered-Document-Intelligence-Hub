from groq import Groq
from app.services.embedding_service import similarity_search
from app.core.config import settings

client = Groq(api_key=settings.GROQ_API_KEY)


def generate_rag_answer(query: str, top_k: int, file_id: str = None):
    docs = similarity_search(query, top_k, file_id)
    context = ""

    for i, d in enumerate(docs):
        context += f"Chunk {i + 1}:\n{d['text']}\n\n"

        prompt = f"""
                 You are an intelligent document assistant.
                    Use the following document context to answer the question.

                    Context:
                    {context}

                    Question:
                    {query}

                    Answer clearly and concisely.
                    """

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "You answer based only on provided context.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    answer = response.choices[0].message.content

    return answer, docs
