from PIPELINE._4_retrieve.multi_stages.hybrid_retriever import normalize_vector_results, vector_search
from pipeline_config import FINAL_CHUNKS_NUM, VECTORDB_FIXEDSIZE_CONNECT_INFO


def normal_retrieve(query, dbinfo=VECTORDB_FIXEDSIZE_CONNECT_INFO):
    docs = vector_search(query, dbinfo)
    normalized_docs = normalize_vector_results(docs)
    normalized_docs = normalized_docs[:FINAL_CHUNKS_NUM]
    return normalized_docs