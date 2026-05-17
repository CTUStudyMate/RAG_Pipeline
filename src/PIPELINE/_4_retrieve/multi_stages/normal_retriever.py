from PIPELINE._4_retrieve.multi_stages.hybrid_retriever import normalize_vector_results, vector_search
from PIPELINE._4_retrieve.utils.get_final_chunk import greedy_add_chunks
from pipeline_config import settings

VECTORDB_CONNECT_INFO = settings.config["vectordb_connect_info"]

def normal_retrieve(query, dbinfo=VECTORDB_CONNECT_INFO):
    docs = vector_search(query, dbinfo)
    normalized_docs = normalize_vector_results(docs)
    final_docs = greedy_add_chunks(normalized_docs)
    return final_docs