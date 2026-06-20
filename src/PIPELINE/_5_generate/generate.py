import json

# from common_utils.debug import log_to_file
from pipeline_config import settings
# from src.used_models.llm.LLM_Factory import get_llm
from pipeline_setup import llm
from pipeline_setup import cursor

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


absenceBasedAbstain_system_prompt = """
You are a helpful assistant that answers user questions using the provided context documents.

## Instructions:
- DATA FIDELITY: Your answer must be strictly faithful to the provided context documents, which are stated ONLY in the "CONTEXT DOCUMENTS" section and the attached images or files if exist.
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
    - "citations": list of verbatim supporting strings from the CONTEXT DOCUMENTS section. If images are provided, and a claim is derived from an image, include the corresponding image reference in citations.

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
            ],
            "type": null
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
    - Any visual claim MUST cite the exact image ID associated with the image from which the information was derived:
        - For images provided in "CONTEXT DOCUMENTS" section, each image ID is introduced immediately before the image input using the format: "Image: <img_id>". 
        - For images come from the user's question or user upload, ALWAYS cite it as: "query_evidence".
    - If a claim is based on image content and no valid image citation is provided, the claim is INVALID and MUST NOT be output.
    - Image citations MUST use only img_id values explicitly provided in the prompt.
    - Do NOT infer, guess, or fabricate image IDs.

    3. GENERAL RULES:
    - If a segment cannot be supported by either:
        (1) a verifiable verbatim text citation, or
        (2) a valid provided image identifier, omit the segment entirely rather than fabricating support.
"""

evidenceBasedSynthesis_system_prompt = """
You are a helpful assistant that answers user questions using the provided context documents.

## Instructions:
- DATA FIDELITY: Your answer must be strictly faithful to the provided context documents, which are stated ONLY in the "CONTEXT DOCUMENTS" section and the attached images or files if exist.
- Do NOT use external knowledge, assumptions, implications, or hallucinated facts.
- If the context does not contain explicit answer sentences, you MAY synthesize an answer ONLY by combining facts that are explicitly stated in the context.
    - You are only allowed to combine facts when:
    (1) each individual fact is explicitly present in the context, AND
    (2) the relationship between those facts is directly stated in the context OR is a trivial logical combination (e.g., cause → effect explicitly stated, definition → example explicitly stated)

    - You MUST NOT:
    - infer new relationships between entities, papers, or categories that are not explicitly stated
    - introduce classification memberships, citations, authorship, or “example-of-category” relationships unless explicitly stated
    - use general world knowledge to bridge missing links

- If the provided context does not contain sufficient information to directly answer the question, do not attempt to guess or output an empty array. Instead, return exactly one segment with "type": "abstained" and the exact text: "The system can't answer this question. Please try again with another question.".
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
    - "citations": list of verbatim supporting strings from the CONTEXT DOCUMENTS section. If images are provided, and a claim is derived from an image, include the corresponding image reference in citations.

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
            ],
            "type": null
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
    - Any visual claim MUST cite the exact image ID associated with the image from which the information was derived:
        - For images provided in "CONTEXT DOCUMENTS" section, each image ID is introduced immediately before the image input using the format: "Image: <img_id>". 
        - For images come from the user's question or user upload, ALWAYS cite it as: "query_evidence".
    - If a claim is based on image content and no valid image citation is provided, the claim is INVALID and MUST NOT be output.
    - Image citations MUST use only img_id values explicitly provided in the prompt.
    - Do NOT infer, guess, or fabricate image IDs.

    3. GENERAL RULES:
    - If a segment cannot be supported by either:
        (1) a verifiable verbatim text citation, or
        (2) a valid provided image identifier, omit the segment entirely rather than fabricating support.
"""

pgdb_connect_info = settings.pgdb_connect_info

def get_base64(img_ids):
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
    
    
def build_content_inputs(docs, q):
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
    
    rows = get_base64(img_ids)
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
        embedded_parts.append(f"\n[{i}]\n{embedded_content}\n")
    
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
         
def build_content_inputs_lcver(docs, q):
    content, context_text, embedded_text = build_content_inputs(
        docs=docs, q=q
    )

    new_content = []

    for item in content:
        if item["type"] == "input_text":
            new_content.append({
                "type": "text",
                "text": item["text"]
            })

        elif item["type"] == "input_image":
            new_content.append({
                "type": "image_url",
                "image_url": {
                    "url": item["image_url"]
                }
            })

        else:
            new_content.append(item)

    return new_content, context_text, embedded_text        

        
# llm = get_llm(LLM_PROVIDER) 


JSON_FIX_PROMPT = """
You are a JSON repair tool.

Your task:
- Convert the given text into VALID JSON.
- Preserve the original content as much as possible.
- Output ONLY valid JSON.
- Do not wrap with markdown code fences.
"""


def generate_answer(query, docs, max_retries=3):
    content, source_context_text, embedded_text = build_content_inputs(
        docs=docs,
        q=query
    )

    # -----------------------
    # PASS 1: STRICT MODE
    # -----------------------
    answer = llm.generate(
        system_prompt=absenceBasedAbstain_system_prompt,
        content=content
    )

    # -----------------------
    # PASS 1 JSON REPAIR LOOP
    # -----------------------
    parsed = None

    for _ in range(max_retries):
        try:
            parsed = json.loads(answer)
            break
        except json.JSONDecodeError:
            repair_prompt = f"""
The following text is invalid JSON.

Fix it into valid JSON.

TEXT:
{answer}
"""

            answer = llm.generate(
                system_prompt=JSON_FIX_PROMPT,
                content=[{
                    "type": "input_text",
                    "text": repair_prompt
                }]
            )

    # nếu vẫn fail sau retry
    if parsed is None:
        return "", source_context_text, docs, embedded_text

    # -----------------------
    # PASS 1 SUCCESS CASE
    # -----------------------
    if isinstance(parsed, list) and len(parsed) > 0:
        return answer, source_context_text, docs, embedded_text

    # -----------------------
    # PASS 2: EVIDENCE SYNTHESIS
    # -----------------------
    print("! Strict-grounded returned empty answer. Turn to Evidence-based.")
    answer = llm.generate(
        system_prompt=evidenceBasedSynthesis_system_prompt,
        content=content
    )

    # -----------------------
    # PASS 2 JSON REPAIR LOOP
    # -----------------------
    parsed = None

    for _ in range(max_retries):
        try:
            parsed = json.loads(answer)
            return answer, source_context_text, docs, embedded_text

        except json.JSONDecodeError:
            repair_prompt = f"""
The following text is invalid JSON.

Fix it into valid JSON.

TEXT:
{answer}
"""

            answer = llm.generate(
                system_prompt=JSON_FIX_PROMPT,
                content=[{
                    "type": "input_text",
                    "text": repair_prompt
                }]
            )

    return "", source_context_text, docs, embedded_text
