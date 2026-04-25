import re

import chromadb
from common_utils.debug import log_to_file
from models import VectorDBConnectIfo
from models.PGDBConnectInfo import PGDBConnectInfo
from pipeline_config import PGDB_HSF_MS_CONNECT_INFO, RRF_RANKING_CONSTANT, RRF_TOP_K, VECTORDB_HSF_MS_CONNECT_INFO
import psycopg

from pipeline_config import EMBEDDING_PROVIDER, VECTOR_RETRIEVE_CHUNKS_LIMIT, TEXT_RETRIEVE_CHUNKS_LIMIT
from used_models.embeddings.embed_factory import EmbeddingService 

def vector_search(query: str, vectordb_connect_info: VectorDBConnectIfo):
    
    vector_db_path = vectordb_connect_info["db_path"]
    vector_db_collection = vectordb_connect_info["collection"]
    embedder = EmbeddingService(provider=EMBEDDING_PROVIDER)
    client = chromadb.PersistentClient(path=vector_db_path)
    collection = client.get_or_create_collection(name=vector_db_collection)
    
    query_emb = embedder.embed(query)
    results = collection.query(
        query_embeddings=query_emb,
        n_results=VECTOR_RETRIEVE_CHUNKS_LIMIT
    )
    return results


def text_search(query: str, pgdb_connect_info):
    # Làm sạch query: Thay thế các ký tự không phải là chữ cái/số (\w) hoặc khoảng trắng (\s) bằng dấu cách.
    #  Việc này giúp ParadeDB không bị lỗi parse syntax mà vẫn giữ nguyên từ khóa để tìm kiếm BM25.
    safe_query = re.sub(r'[^\w\s]', ' ', query)
    safe_query = re.sub(r'\s+', ' ', safe_query).strip()

    try:
        conn = psycopg.connect(
            host=pgdb_connect_info["host"],
            port=pgdb_connect_info["port"],
            dbname=pgdb_connect_info["db_name"],
            user=pgdb_connect_info["user"],
            password=pgdb_connect_info["password"],
            connect_timeout=5   # tránh treo vô hạn
        )
    except Exception as e:
        print(f"[DB ERROR] Cannot connect: {e}")
        return []  

    try:
        print("Connect ok")
        cur = conn.cursor()
        table_name = pgdb_connect_info["table_name"]
        
        cur.execute(f"""
            SELECT id, document_id, text_content, metadata, paradedb.score(id) AS score
            FROM {table_name}
            WHERE text_content @@@ %s
            ORDER BY score DESC
            LIMIT {TEXT_RETRIEVE_CHUNKS_LIMIT};
        """, (safe_query,))
        
        rows = cur.fetchall()
        return rows

    except Exception as e:
        print(f"[QUERY ERROR] {e}")
        return []

    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass


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
def rrf_merge(vector_docs, bm25_docs, k=RRF_RANKING_CONSTANT, top_k=RRF_TOP_K):
    scores = {}

    # vector ranking
    for rank, doc in enumerate(vector_docs, start=1):
        doc_id = doc["doc_id"]
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank)

    # bm25 ranking
    for rank, doc in enumerate(bm25_docs, start=1):
        doc_id = doc["doc_id"]
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank)

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    doc_map = {doc["doc_id"]: doc for doc in vector_docs + bm25_docs}

    results = []
    for doc_id, score in ranked[:top_k]:
        doc = doc_map[doc_id]
        doc["rrf_score"] = score
        results.append(doc)

    return results     

        
def hybrid_retrieve(query: str, 
                    pgdb_connect_info: PGDBConnectInfo = PGDB_HSF_MS_CONNECT_INFO, 
                    vectordb_connect_info: VectorDBConnectIfo = VECTORDB_HSF_MS_CONNECT_INFO):
    vector_based_results = vector_search(query=query, vectordb_connect_info=vectordb_connect_info)
    text_based_results = text_search(query=query, pgdb_connect_info=pgdb_connect_info)
    
    vector_docs = normalize_vector_results(vector_based_results)
    bm25_docs = normalize_text_results(text_based_results)
    
    hybrid_docs = rrf_merge(vector_docs, bm25_docs)
    return hybrid_docs

        
    
    
    



    