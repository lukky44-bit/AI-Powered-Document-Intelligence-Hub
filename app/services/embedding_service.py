import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.config import settings

# Embedding model
embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

PERSIST_DIR = settings.EMBEDDINGS_DIR


def get_vector_store():
    if os.path.exists(PERSIST_DIR) and os.listdir(PERSIST_DIR):
        return Chroma(persist_directory=PERSIST_DIR, embedding_function=embedding_model)
    return None


def chunk_text(text: str):
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    return splitter.split_text(text)


def store_text(text: str, doc_id: str):
    chunks = chunk_text(text)

    documents = []
    for i, chunk in enumerate(chunks):
        documents.append(
            Document(page_content=chunk, metadata={"doc_id": doc_id, "chunk_id": i})
        )

    vectorstore = get_vector_store()

    if vectorstore:
        vectorstore.add_documents(documents)
    else:
        vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=embedding_model,
            persist_directory=PERSIST_DIR,
        )

    return {
        "message": "Document chunked and stored successfully",
        "doc_id": doc_id,
        "total_chunks": len(chunks),
    }


def similarity_search(
    query: str,
    top_k: int = 15,
    file_id: str = None,
    file_ids: list[str] | None = None,
):
    vectorstore = get_vector_store()
    if not vectorstore:
        raise ValueError("Vector store is empty. Store documents first.")

    if file_id:
        results = vectorstore.similarity_search(
            query, k=top_k, filter={"doc_id": file_id}
        )
    elif file_ids is not None:
        if not file_ids:
            return []

        try:
            results = vectorstore.similarity_search(
                query,
                k=top_k,
                filter={"doc_id": {"$in": file_ids}},
            )
        except Exception:
            # Fallback for stores that don't support $in filters.
            candidate_k = max(top_k * 8, top_k)
            candidates = vectorstore.similarity_search(query, k=candidate_k)
            results = [
                d for d in candidates if d.metadata.get("doc_id") in set(file_ids)
            ][:top_k]
    else:
        results = vectorstore.similarity_search(query, k=top_k)

    formatted = []
    for doc in results:
        formatted.append({"text": doc.page_content, "metadata": doc.metadata})

    return formatted


def delete_file_embeddings(file_id: str):
    """
    Deletes all vector chunks belonging to a file
    """
    vectorstore = get_vector_store()
    vectorstore.delete(where={"doc_id": file_id})
