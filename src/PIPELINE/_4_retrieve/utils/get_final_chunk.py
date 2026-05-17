from PIPELINE._3_chunk.common_utils import mannual_token_count
from pipeline_config import settings

IMAGE_TOKEN_ESTIMATE = settings.config["image_token_estimate"]
TOKEN_BUDGET = settings.config["token_budget"]
    
def greedy_add_chunks (ranked_chunks, token_budget=TOKEN_BUDGET):
    total_tokens = 0
    selected_chunks = []
    for chunk in ranked_chunks:
        chunk_token = mannual_token_count(chunk["text"])
        num_images = len(chunk["metadata"].get("image", []))
        chunk_token += num_images * IMAGE_TOKEN_ESTIMATE
        if total_tokens+chunk_token <= token_budget:
            selected_chunks.append(chunk)
            total_tokens += chunk_token
        else:
            continue
    return selected_chunks    