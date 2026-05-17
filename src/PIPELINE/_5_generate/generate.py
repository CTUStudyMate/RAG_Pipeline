import json

# from common_utils.debug import log_to_file
from pipeline_config import settings
# from src.used_models.llm.LLM_Factory import get_llm
from pipeline_setup import llm

MAX_IMAGES_PER_LLMCALL = settings.config["max_images_per_llmcall"]

# def build_context(docs):
#     context_parts = []
#     images = []
#     image_refs = []
#     for i, doc in enumerate(docs, start=1):
#         content = doc.get("text", "")
#         metadata = doc.get("metadata", {})

#         # text context
#         context_parts.append(
#             f"[{i}]\n"
#             f"{content}\n"
#         )

#         # if "image" in metadata and metadata["image"]:
#         #     for j, img in enumerate(metadata["image"]):
#         #         img_id = f"img_{i}_{j}"
#         #         images.append({
#         #             "id": img_id,
#         #             "data": img
#         #         })
#         #         image_refs.append(
#         #             f"IMAGE_{len(image_refs)}: img_id={img_id}, context document={i}"
#         #         )
        
        

#     context_text = "\n".join(context_parts)
#     return context_text, images, image_refs


system_prompt = """
You are a helpful assistant that answers user questions using the provided context documents.

## Instructions:
- DATA FIDELITY: Your answer must be strictly faithful to the provided context documents, which are the text stated in the <CONTEXT DOCUMENTS></CONTEXT DOCUMENTS> tag and the attached images or files if exist.
- Do NOT use external knowledge, assumptions, implications, or hallucinated facts.
- If the context does not contain enough information to answer the question, return an empty array.
- Be concise and precise.

## Output format:
    Return a JSON array. Each item represents one segment of the final answer.

    Each segment has three fields:
    - "role": how this segment should be rendered when concatenated. Must be one of:
        - "sentence"      → append directly after previous segment (separated by a space)
        - "paragraph"     → start a new paragraph (insert blank line before this segment)
        - "bullet"        → render as a bullet point (prefix with "- ")
        - "bullet_intro"  → the sentence that introduces a bullet list (followed by ":")
    - "segment": the text content of this segment (one factual claim)
    - "citations": list of verbatim supporting strings from the <CONTEXT DOCUMENTS></CONTEXT DOCUMENTS> tag. If image mappings are provided, and a claim is derived from an image, include the corresponding image reference in citations.

    Expected JSON Structure:
    [
        {
            "role": "paragraph" | "bullet_intro" | "bullet",
            "segment": "one factual claim",
            "citations": [
                {
                    "type": "source_text",
                    "content": "exact verbatim supporting text from the context",
                    "img_id": null
                },
                {
                    "type": "img",
                    "content": null,
                    "img_id": "image_0_1"
                }
            ]
        }
    ]  
    

## CITATION RULES:

    1. TEXT CITATIONS:
    - Every text citation must be a VERBATIM substring of the text inside "CONTEXT DOCUMENTS" section.
    - Before including a text citation, verify that the cited content appears word-for-word in the provided context.
    - Text citations must NOT be paraphrased, modified, truncated, or shortened (e.g., using "...").
    - Each text citation must be a complete sentence or phrase from the original context text.

    2. IMAGE CITATION RULE:
    - Any claim derived from visual information MUST include at least one image citation.
    - Each image is introduced immediately before the image input using the format: "Image: <img_id>".
    - Any visual claim MUST cite the exact img_id associated with the image from which the information was derived.
    - If a claim is based on image content and no valid image citation is provided, the claim is INVALID and MUST NOT be output.
    - Image citations MUST use only img_id values explicitly provided in the prompt.
    - Do NOT infer, guess, or fabricate image IDs.

    3. GENERAL RULES:
    - If a segment cannot be supported by either:
        (1) a verifiable verbatim text citation, or
        (2) a valid provided image identifier, omit the segment entirely rather than fabricating support.
"""

# def build_prompt(query, context, image_refs):
#     image_mapping_section = (
#     "\n".join(image_refs)
#     if image_refs
#     else "No images retrieved."
# )
#     return f"""
# ## CONTEXT DOCUMENTS
# <CONTEXT DOCUMENTS>
# {context}
# </CONTEXT DOCUMENTS>

# ## IMAGE MAPPING
# <IMAGE MAPPING>
# {image_mapping_section}
# </IMAGE MAPPING>

# ## USER QUESTION
# {query}
#"""
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
    context_parts = []
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
        
        content.append({
            "type": "input_text", 
             "text": f"\n[{i}]\n{text_content}\n"
        })
        context_parts.append(f"\n[{i}]\n{text_content}\n")
    
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
    return content, context_text, img_ids
         
 

        
# llm = get_llm(LLM_PROVIDER) 


def generate_answer(query, docs, max_retries=2):
    # docs đưa vô hàm này là phải được chốt rồi
    content, context_text, img_ids = build_content_inputs(docs=docs, q=query)
    
    # for attempt in range(max_retries + 1):
    #     answer = llm.generate(system_prompt=system_prompt, content=content)
    #     segments = json.loads(answer)
        
    #     violations = validate_citations(segments)
    #     if not violations:
    #         return segments, context_text
        
    #     if attempt < max_retries:
    #         prompt = build_prompt_with_feedback(
    #             query, context_text, image_refs, violations
    #         )
    answer = llm.generate(system_prompt=system_prompt, content=content)
    return answer, context_text, docs, img_ids

# def validate_citations(segments, image_refs):
#     """Trả về list các vi phạm."""    
#     violations = []
#     valid_img_ids = [img_ref.split(": ")[0] for img_ref in image_refs]
    
#     for i, seg in enumerate(segments):
#         citations = seg.get("citations", [])
        
#         # Vi phạm: citations rỗng hoàn toàn
#         if not citations:
#             violations.append(
#                 f"Segment {i} ('{seg['segment'][:40]}...') "
#                 f"has no citations."
#             )
#             continue
        
#         # Vi phạm: img_id không hợp lệ
#         for c in citations:
#             if c["type"] == "img" and c["img_id"] not in valid_img_ids:
#                 violations.append(
#                     f"Segment {i}: invalid img_id '{c['img_id']}'. "
#                     f"Valid IDs: {valid_img_ids}"
#                 )
    
#     return violations


# def build_prompt_with_feedback(query, context, image_refs, violations):
#     feedback = "\n".join(f"- {v}" for v in violations)
#     return f"""
# ## CONTEXT DOCUMENTS
# <CONTEXT DOCUMENTS>
# {context}
# </CONTEXT DOCUMENTS>

# ## IMAGE MAPPING
# <IMAGE MAPPING>
# {chr(10).join(image_refs)}
# </IMAGE MAPPING>

# ## PREVIOUS ATTEMPT VIOLATIONS
# Your previous response had the following citation errors.
# Fix ALL of them in your new response:
# {feedback}

# ## USER QUESTION
# {query}
# """