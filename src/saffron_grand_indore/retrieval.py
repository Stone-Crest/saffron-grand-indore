from .knowledge import vectorstore
from .config import (
    CANDIDATE_CEILING, DOC_INCLUSION_MAX_DISTANCE, CITATION_MAX_DISTANCE,
    SOURCE_RELEVANCE_MARGIN, MAX_CONTEXT_CHARS,
)


def enforce_context_budget(docs, max_chars=MAX_CONTEXT_CHARS):
    trimmed, total = [], 0
    for doc in docs:
        total += len(doc.page_content)
        if total > max_chars and trimmed:
            break
        trimmed.append(doc)
    return trimmed


def retrieve_with_confidence(question):
    collection_size = vectorstore._collection.count()
    k = min(CANDIDATE_CEILING, collection_size)

    result = vectorstore.similarity_search_with_score(question, k=k)
    if not result:
        return [], []

    result = sorted(result, key=lambda x: x[1])
    best_score = result[0][1]

    included = [(doc, score) for doc, score in result if score <= DOC_INCLUSION_MAX_DISTANCE]
    if not included:
        included = result[:1]

    docs = enforce_context_budget([doc for doc, _ in included])

    if best_score > CITATION_MAX_DISTANCE:
        relevant_types = []
    else:
        relevant_types = sorted({
            doc.metadata.get("doc_type", "info")
            for doc, score in included
            if score <= best_score + SOURCE_RELEVANCE_MARGIN
        })

    return docs, relevant_types