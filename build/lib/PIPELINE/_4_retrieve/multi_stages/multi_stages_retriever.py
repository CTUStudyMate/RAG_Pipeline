from PIPELINE._4_retrieve.multi_stages.cross_encoder import CrossEncoderService
from PIPELINE._4_retrieve.multi_stages.hybrid_retriever import hybrid_retrieve
from PIPELINE._4_retrieve.utils.common_helpers import print_retrieved_docs
from PIPELINE._4_retrieve.utils.get_final_chunk import greedy_add_chunks
from common_utils.debug import log_to_file
from pipeline_config import FINAL_CHUNKS_NUM


reranker = CrossEncoderService()

def multi_stages_retrieve(query: str):
    #hybrid search - rrf - retrieve
    hybrid_docs = hybrid_retrieve(query)
    
    reranked_docs = reranker.rerank(query, hybrid_docs)
    final_docs = greedy_add_chunks(reranked_docs)
    return final_docs

# docs = multi_stages_retrieve("What is the difference between technical and business quality? Explain why each is important.")
# print(docs[0])