import re

import chromadb
from common_utils.debug import log_to_file
from models.VectorDBConnectIfo import VectorDBConnectIfo
from models.PGDBConnectInfo import PGDBConnectInfo
from pipeline_config import settings

import psycopg

from used_models.embeddings.embed_factory import EmbeddingService 

PGDB_HSF_MS_CONNECT_INFO = settings.pgdb_connect_info
RRF_RANKING_CONSTANT = settings.config["rrf_ranking_constant"]
RRF_TOP_K = settings.config["rrf_top_k"]
VECTORDB_HSF_MS_CONNECT_INFO = settings.config["vectordb_connect_info"]

EMBEDDING_PROVIDER = settings.config["embedding_provider"]
VECTOR_RETRIEVE_CHUNKS_LIMIT = settings.config["vector_retrieve_chunks_limit"]
TEXT_RETRIEVE_CHUNKS_LIMIT = settings.config["text_retrieve_chunks_limit"]

embedder = EmbeddingService(provider=EMBEDDING_PROVIDER)

_default_db_path = VECTORDB_HSF_MS_CONNECT_INFO["db_path"]
_default_collection_name = VECTORDB_HSF_MS_CONNECT_INFO["collection"]

_default_client = chromadb.PersistentClient(path=_default_db_path)
_default_collection = _default_client.get_or_create_collection(
    name=_default_collection_name
)


def vector_search(
    query: str,
    vectordb_connect_info: VectorDBConnectIfo | None = None # chỗ này có thể bug vì đáng ra nó truy cập kiểu [""] do config được nhét trong yaml chứ không phải dùng dấu . như trong class
):
    if vectordb_connect_info is None:
        client = _default_client
        collection = _default_collection
    else:
        client = chromadb.PersistentClient(
            path=vectordb_connect_info["db_path"]
        )
        collection = client.get_or_create_collection(
            name=vectordb_connect_info["collection"]
        )
    
    query_emb = embedder.embed(query)
    results = collection.query(
        query_embeddings=query_emb,
        n_results=VECTOR_RETRIEVE_CHUNKS_LIMIT
    )
    filtered_docs = []
    filtered_distances = []

    for doc, dist in zip(results["documents"][0], results["distances"][0]):
        cosine_sim = 1 - dist  # nếu metric = cosine

        if cosine_sim >= 0.4:
            filtered_docs.append(doc)
            filtered_distances.append(dist)

    results["documents"] = [filtered_docs]
    results["distances"] = [filtered_distances]

    return results


def text_search(query: str, cursor):
    # Làm sạch query: Thay thế các ký tự không phải là chữ cái/số (\w) hoặc khoảng trắng (\s) bằng dấu cách.
    #  Việc này giúp ParadeDB không bị lỗi parse syntax mà vẫn giữ nguyên từ khóa để tìm kiếm BM25.
    safe_query = re.sub(r'[^\w\s]', ' ', query)
    safe_query = re.sub(r'\s+', ' ', safe_query).strip()

    
    cur = cursor
    table_name = settings.pgdb_connect_info.chunks_table
    
    cur.execute(f"""
        SELECT id, document_id, text_content, metadata, paradedb.score(id) AS score
        FROM {table_name}
        WHERE search_content @@@ %s
        ORDER BY score DESC
        LIMIT {TEXT_RETRIEVE_CHUNKS_LIMIT};
    """, (safe_query,))
    
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
    
    
def print_normalized_docs(docs):
        # {
        #     "doc_id": doc_id,
        #     "text": text,
        #     "metadata": meta,
        #     "score": 1 - dist  # convert distance → similarity
        # }    
    for doc in docs:
        log_to_file(f"**{doc["doc_id"][:300]}")
        log_to_file(doc["text"])
        log_to_file(doc["score"])
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

        
def hybrid_retrieve(query: str, cursor, vector_weight, bm25_weight,
                    vectordb_connect_info: VectorDBConnectIfo | None = None):
    vector_based_results = vector_search(query=query, vectordb_connect_info=vectordb_connect_info)
    text_based_results = text_search(query=query, cursor=cursor)
    
    vector_docs = normalize_vector_results(vector_based_results)
    bm25_docs = normalize_text_results(text_based_results)
    
    hybrid_docs = rrf_merge(vector_docs, bm25_docs, vector_weight=vector_weight, bm25_weight=bm25_weight)
    return hybrid_docs

        
    
    
    



    