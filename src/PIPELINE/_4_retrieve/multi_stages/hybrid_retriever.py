import logging
import re
import time

import chromadb
from chromadb.errors import InternalError

from pipeline_config import settings
from pipeline_setup import _default_collection, embedder, pool

RRF_RANKING_CONSTANT = settings.config["rrf_ranking_constant"]
RRF_TOP_K = settings.config["rrf_top_k"]
VECTOR_RETRIEVE_CHUNKS_LIMIT = settings.config["vector_retrieve_chunks_limit"]
TEXT_RETRIEVE_CHUNKS_LIMIT = settings.config["text_retrieve_chunks_limit"]
bm25_weight = settings.config["bm25_weight"]
vector_weight = settings.config["vector_weight"]
VECTOR_QUERY_MAX_ATTEMPTS = 3

logger = logging.getLogger(__name__)


def _empty_vector_results():
    """Return the Chroma result shape when vector retrieval is unavailable."""
    return {
        "ids": [[]],
        "documents": [[]],
        "metadatas": [[]],
        "distances": [[]],
    }


def _open_vector_collection():
    """Open a fresh client after Chroma reports a transient index lookup error."""
    vector_db = settings.config["vectordb_connect_info"]
    client = chromadb.PersistentClient(path=vector_db["db_path"])
    return client.get_collection(vector_db["collection"])

def vector_search(query: str, document_ids: list[int] | None = None):
    collection = _default_collection
    
    query_emb = embedder.embed(query)
    query_options = {
        "query_embeddings": query_emb,
        "n_results": VECTOR_RETRIEVE_CHUNKS_LIMIT,
    }

    if document_ids is not None:
        query_options["where"] = {
            "document": {
                "$in": [str(document_id) for document_id in document_ids],
            }
        }

    for attempt in range(VECTOR_QUERY_MAX_ATTEMPTS):
        try:
            results = collection.query(**query_options)
            break
        except InternalError as error:
            if attempt == VECTOR_QUERY_MAX_ATTEMPTS - 1:
                logger.exception(
                    "Chroma vector retrieval failed after %s attempts; falling back to BM25.",
                    VECTOR_QUERY_MAX_ATTEMPTS,
                )
                return _empty_vector_results()

            logger.warning(
                "Chroma returned an internal index error (attempt %s/%s): %s. Retrying.",
                attempt + 1,
                VECTOR_QUERY_MAX_ATTEMPTS,
                error,
            )
            time.sleep(0.1 * (attempt + 1))
            collection = _open_vector_collection()

    filtered_docs = []
    filtered_distances = []

    for doc, dist in zip(results["documents"][0], results["distances"][0]):
        cosine_sim = 1 - dist  # nếu metric = cosine

        if cosine_sim >= 0.4:
            filtered_docs.append(doc)
            filtered_distances.append(dist)
        else:
            print("Document has similarity lower than 0.4")

    results["documents"] = [filtered_docs]
    results["distances"] = [filtered_distances]

    return results


def text_search(query: str, document_ids: list[int] | None = None):
    # Làm sạch query: Thay thế các ký tự không phải là chữ cái/số (\w) hoặc khoảng trắng (\s) bằng dấu cách.
    #  Việc này giúp ParadeDB không bị lỗi parse syntax mà vẫn giữ nguyên từ khóa để tìm kiếm BM25.
    safe_query = re.sub(r'[^\w\s]', ' ', query)
    safe_query = re.sub(r'\s+', ' ', safe_query).strip()
    
    table_name = settings.pgdb_connect_info.chunks_table
    
    with pool.connection() as conn:
        with conn.cursor() as cur:
            if document_ids is None:
                cur.execute(f"""
                    SELECT id, document_id, text_content, metadata, paradedb.score(id) AS score
                    FROM {table_name}
                    WHERE search_content @@@ %s
                    ORDER BY score DESC
                    LIMIT {TEXT_RETRIEVE_CHUNKS_LIMIT};
                """, (safe_query,))
            else:
                cur.execute(f"""
                    SELECT id, document_id, text_content, metadata, paradedb.score(id) AS score
                    FROM {table_name}
                    WHERE search_content @@@ %s
                      AND metadata ->> 'document' = ANY(%s)
                    ORDER BY score DESC
                    LIMIT {TEXT_RETRIEVE_CHUNKS_LIMIT};
                """, (
                    safe_query,
                    [str(document_id) for document_id in document_ids],
                ))
            
            rows = cur.fetchall()
    
    return rows

        

# Normalize to the same format from 2 retrieve sources    
def normalize_vector_results(results):
    ids = results["ids"][0]
    docs = results["documents"][0]
    metas = results["metadatas"][0]
    distances = results["distances"][0]

    return [
        {
            "doc_id": doc_id,
            "text": text,
            "metadata": meta,
            "score": 1 - dist  # convert distance → similarity
        }
        for doc_id, text, meta, dist in zip(ids, docs, metas, distances)
    ]


def normalize_text_results(rows):
    return [
        {
            "doc_id": document_id,
            "text": text_content,
            "metadata": metadata,
            "score": score
        }
        for _, document_id, text_content, metadata, score in rows
    ]   
    
    
# def print_normalized_docs(docs):
#         # {
#         #     "doc_id": doc_id,
#         #     "text": text,
#         #     "metadata": meta,
#         #     "score": 1 - dist  # convert distance → similarity
#         # }    
#     for doc in docs:
#         log_to_file(f"**{doc["doc_id"][:300]}")
#         log_to_file(doc["text"])
#         log_to_file(doc["score"])
# RRF
def rrf_merge(
    vector_docs,
    bm25_docs,
    vector_weight=0.75,
    bm25_weight=0.25,
    k=RRF_RANKING_CONSTANT,
    top_k=RRF_TOP_K
):
    scores = {}

    # -------------------------
    # vector ranking
    # -------------------------
    for rank, doc in enumerate(vector_docs, start=1):
        doc_id = doc["doc_id"]

        scores[doc_id] = (
            scores.get(doc_id, 0)
            + vector_weight * (1 / (k + rank))
        )

    # -------------------------
    # bm25 ranking
    # -------------------------
    for rank, doc in enumerate(bm25_docs, start=1):
        doc_id = doc["doc_id"]

        scores[doc_id] = (
            scores.get(doc_id, 0)
            + bm25_weight * (1 / (k + rank))
        )

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    doc_map = {
        doc["doc_id"]: doc
        for doc in vector_docs + bm25_docs
    }

    results = []

    for doc_id, score in ranked[:top_k]:
        doc = doc_map[doc_id].copy()
        doc["rrf_score"] = score
        results.append(doc)

    return results  


  
def hybrid_retrieve(query: str, document_ids: list[int] | None = None):
    vector_based_results = vector_search(
        query=query,
        document_ids=document_ids,
    )
    text_based_results = text_search(
        query=query,
        document_ids=document_ids,
    )
    
    vector_docs = normalize_vector_results(vector_based_results)
    bm25_docs = normalize_text_results(text_based_results)
    
    hybrid_docs = rrf_merge(vector_docs=vector_docs, bm25_docs=bm25_docs, bm25_weight=bm25_weight, vector_weight=vector_weight)
    return hybrid_docs

        
    
    
    



    
