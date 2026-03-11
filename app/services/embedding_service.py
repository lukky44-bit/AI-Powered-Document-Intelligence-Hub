import os
from typing import Any

from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.config import settings

# Embedding model
embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

PERSIST_DIR = settings.EMBEDDINGS_DIR
HYBRID_WEIGHTS = [0.5, 0.5]


def get_vector_store():
    if os.path.exists(PERSIST_DIR) and os.listdir(PERSIST_DIR):
        return Chroma(persist_directory=PERSIST_DIR, embedding_function=embedding_model)
    return None


def _build_doc_filter(file_id: str | None = None, file_ids: list[str] | None = None):
    if file_id:
        return {"doc_id": file_id}

    if file_ids is not None:
        return {"doc_id": {"$in": file_ids}}

    return None


def _filter_documents_by_scope(
    documents: list[Document],
    file_id: str | None = None,
    file_ids: list[str] | None = None,
):
    allowed_file_ids = set(file_ids) if file_ids is not None else None

    filtered = []
    for doc in documents:
        doc_file_id = doc.metadata.get("doc_id")

        if file_id and doc_file_id != file_id:
            continue

        if allowed_file_ids is not None and doc_file_id not in allowed_file_ids:
            continue

        filtered.append(doc)

    return filtered


def _load_documents_for_bm25(
    vectorstore: Chroma,
    file_id: str | None = None,
    file_ids: list[str] | None = None,
):
    where_filter = _build_doc_filter(file_id=file_id, file_ids=file_ids)
    payload: dict[str, Any]

    try:
        if where_filter:
            payload = vectorstore.get(
                where=where_filter,
                include=["documents", "metadatas"],
            )
        else:
            payload = vectorstore.get(include=["documents", "metadatas"])
    except Exception:
        payload = vectorstore.get(include=["documents", "metadatas"])

    raw_documents = payload.get("documents") or []
    raw_metadatas = payload.get("metadatas") or [{} for _ in raw_documents]

    documents = []
    for text, metadata in zip(raw_documents, raw_metadatas):
        documents.append(Document(page_content=text, metadata=metadata or {}))

    return _filter_documents_by_scope(documents, file_id=file_id, file_ids=file_ids)


def _create_bm25_retriever(
    vectorstore: Chroma,
    top_k: int,
    file_id: str | None = None,
    file_ids: list[str] | None = None,
):
    documents = _load_documents_for_bm25(
        vectorstore,
        file_id=file_id,
        file_ids=file_ids,
    )
    if not documents:
        return None

    bm25_retriever = BM25Retriever.from_documents(documents)
    bm25_retriever.k = top_k
    return bm25_retriever


def _create_chroma_retriever(
    vectorstore: Chroma,
    top_k: int,
    file_id: str | None = None,
    file_ids: list[str] | None = None,
):
    search_kwargs = {"k": top_k}
    where_filter = _build_doc_filter(file_id=file_id, file_ids=file_ids)

    if where_filter:
        search_kwargs["filter"] = where_filter

    return vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs=search_kwargs,
    )


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
    if file_ids is not None and not file_ids:
        return []

    vectorstore = get_vector_store()
    if not vectorstore:
        raise ValueError("Vector store is empty. Store documents first.")

    bm25_retriever = _create_bm25_retriever(
        vectorstore,
        top_k=top_k,
        file_id=file_id,
        file_ids=file_ids,
    )
    if not bm25_retriever:
        return []

    chroma_retriever = _create_chroma_retriever(
        vectorstore,
        top_k=top_k,
        file_id=file_id,
        file_ids=file_ids,
    )

    ensemble_retriever = EnsembleRetriever(
        retrievers=[bm25_retriever, chroma_retriever],
        weights=HYBRID_WEIGHTS,
    )

    try:
        results = ensemble_retriever.invoke(query)
    except Exception:
        fallback_chroma_retriever = vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": max(top_k * 4, top_k)},
        )
        fallback_ensemble = EnsembleRetriever(
            retrievers=[bm25_retriever, fallback_chroma_retriever],
            weights=HYBRID_WEIGHTS,
        )
        results = fallback_ensemble.invoke(query)

    results = _filter_documents_by_scope(
        results,
        file_id=file_id,
        file_ids=file_ids,
    )[:top_k]

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
