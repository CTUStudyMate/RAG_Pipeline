from PIPELINE._4_retrieve.multi_stages.cross_encoder import CrossEncoderService
from PIPELINE._4_retrieve.multi_stages.hybrid_retriever import hybrid_retrieve
from PIPELINE._4_retrieve.utils.common_helpers import print_retrieved_docs
from PIPELINE._4_retrieve.utils.get_final_chunk import greedy_add_chunks
from common_utils.debug import log_to_file


reranker = CrossEncoderService()

def multi_stages_retrieve(
    query: str,
    document_ids: list[int] | None = None,
):
    if document_ids == []:
        return []

    #hybrid search - rrf - retrieve
    hybrid_docs = hybrid_retrieve(
        query=query,
        document_ids=document_ids,
    )
    
    # reranked_docs = reranker.rerank(query, hybrid_docs)
    final_docs = greedy_add_chunks(hybrid_docs) # add tới khi đầy token budget
    print("final docs:")
    for doc in final_docs:
        print(doc.get("doc_id"))
    return final_docs
