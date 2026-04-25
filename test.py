from PIPELINE._3_chunk.strategies.HSF.atomic_db_helpers.db_helpers import connect_db
from PIPELINE._4_retrieve.multi_stages.hybrid_retriever import normalize_vector_results, vector_search
from common_utils.debug import log_to_file
from pipeline_config import VECTORDB_HSF_MS_CONNECT_INFO

q = "what is the difference between software engineering and computer science?"
results = vector_search(vectordb_connect_info=VECTORDB_HSF_MS_CONNECT_INFO, query=q)
docs = normalize_vector_results(results)
print(len(results))
log_to_file(results)

log_to_file("________________________________________")
print(len(docs))
log_to_file(docs)
