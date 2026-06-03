import json

# from common_utils.debug import log_to_file
from pipeline_config import settings
# from src.used_models.llm.LLM_Factory import get_llm
from pipeline_setup import llm

MAX_IMAGES_PER_LLMCALL = settings.config["max_images_per_llmcall"]

system_prompt = """
You are a helpful assistant.

        Instructions:
        - Use ONLY the information provided from the context to answer the questions.
        - If the context doesn't provide enough information for you to answer, say "The chatbot can't answer this question. Please try again with another question.".
        - Be concise but clear.
        - Do NOT hallucinate.
"""

pgdb_connect_info = settings.pgdb_connect_info

def get_base64(img_ids, cursor):
    if not img_ids:
        return []
    placeholders = ",".join(["%s"] * len(img_ids))
    query = f"""
        SELECT img_id, base64
        FROM {pgdb_connect_info.images_table}
        WHERE img_id IN ({placeholders})
    """
    cursor.execute(query, img_ids)
    return cursor.fetchall()
    
    
def build_content_inputs(docs, q, cursor):
    content = []
    context_parts = [] # chỉ source text từ tài liệu 
    embedded_parts = [] # nội dung được dùng để embed và retrieve, bao gồm cả mô tả ảnh
    img_ids = []
    current_img_num = 0
    
    # lấy hết img_ids để fetch từ db ra một lượt
    for doc in docs:
        metadata = doc.get("metadata", {})
        if "images" in metadata and metadata["images"]:
            img_ids.extend(metadata["images"])
    
    rows = get_base64(img_ids, cursor)
    img_map = {img_id: base64 for img_id, base64 in rows}

    # tạo map với key là img_id và value là base64 từ kết quả trên       
    content.append({
        "type": "input_text",
        "text": f"### CONTEXT DOCUMENTS\n"
    })  
    for i, doc in enumerate(docs):
        text_content = doc.get("text", "")
        metadata = doc.get("metadata", {})
        embedded_content = metadata.get("embeded_content", "")
        
        content.append({
            "type": "input_text", 
             "text": f"\n[{i}]\n{text_content}\n"
        })
        context_parts.append(f"\n[{i}]\n{text_content}\n") # này mới là thứ đưa vào cho llm trả lời
        embedded_parts.append(f"\n[{i}]\n{embedded_content}\n") # cái này lấy để sau đánh giá retrieve
    
        if "images" in metadata and metadata["images"]:
            for j, img in enumerate(metadata["images"]):
                if current_img_num < MAX_IMAGES_PER_LLMCALL:
                    img_id = img
                    content.append({
                        "type": "input_text",
                        "text": f"\n\nImage: {img_id}"
                    })
                    url = img_map.get(img_id, None)
                    if url is None:
                        continue
                    content.append({
                        "type": "input_image",
                        "image_url": url    
                    })
                    current_img_num += 1
                else: 
                    break 
                
                 
    content.append({
        "type": "input_text",
        "text": f"""### USER QUESTION\n{q}\n### ANSWER"""
    }) 
    context_text = "\n".join(context_parts)
    embedded_text = "\n".join(embedded_parts)
    return content, context_text, embedded_text
         

def generate_answer_without_citation(cursor, query, docs, max_retries=3):
    content, source_context_text, embedded_text = build_content_inputs(
        docs=docs,
        q=query,
        cursor=cursor
    )
    answer = llm.generate(
        system_prompt=system_prompt,
        content=content
    )

    return answer, source_context_text, docs, embedded_text
