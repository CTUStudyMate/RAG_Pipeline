from openai import OpenAI


from common_utils.debug import log_to_file
from pipeline_config import LLM_PROVIDER, MAX_IMAGES_PER_LLMCALL
from src.used_models.llm.LLM_Factory import get_llm

# client = OpenAI()

def build_context(docs):
    context_parts = []
    images = []
    image_refs = []
    for i, doc in enumerate(docs, start=1):
        content = doc.get("text", "")
        metadata = doc.get("metadata", {})

        # text context
        context_parts.append(
            f"[{i}]\n"
            f"{content}\n"
        )

        if "image" in metadata and metadata["image"]:
            for j, img in enumerate(metadata["image"]):
                img_id = f"img_{i}_{j}"
                images.append({
                    "id": img_id,
                    "data": img
                })
                image_refs.append(f"[{i}] -> {img_id}")

    context_text = "\n".join(context_parts)
    return context_text, images

# prompt_str = f"""
# You are a helpful assistant answering questions based ONLY on the provided context.

#         Instructions:
#         - Use ONLY the information from the context below
#         - If the answer is not in the context, say you don't have enough information to answer the question
#         - Be concise but clear
#         - Do NOT hallucinate
        
# """

# prompt_str = f"""
# You are a helpful assistant.

#         Instructions:
#         - Use ONLY the information provided from the context documents below to answer the questions.
#         - If the context doesn't provide enough information for you to answer, say you don't have enough information to answer the question.
#         - Return JSON in the following format:
#             {{
#                 "answer": your full answer,
#                 "segments": 
#                 [
#                     {{
#                     "text": an exact span in your answer,
#                     "sources": document number for that span (e.g. [1])
#                     }},
#                     {{
#                     "text": the next span in your answer,
#                     "sources": document number for that span
#                     }},
#                     ...
#                 ]
#             }}
# """

# system_prompt = f"""
# You are a helpful assistant that answers user questions using the provided context documents.

# Instructions:
# - DATA FIDELITY: Your answer must be strictly faithful to the provided context documents.
# - Use ONLY information explicitly stated in the source text.
# - Do NOT use external knowledge, assumptions, implications, or hallucinated facts.
# - If the context does not contain enough information to answer the question, return an empty array.
# - Be concise and precise.

# Output format:
# Return a JSON array.

# Each item in the array must represent EXACTLY ONE atomic factual claim. When all items are concatenated in order, they should form a coherent answer.

# Format:
# [
#     {{
#         "segment": "one atomic factual claim",
#         "citations": [
#             "exact verbatim supporting text from the context"
#         ]
#     }}
# ]

# Citation rules:
# - Every citation must be copied EXACTLY from the context documents.
# - Citations must directly support the segment semantically, not just be topically related.
# - Do NOT provide unrelated or weakly related citations.
# - Do NOT combine multiple independent claims into one segment.
# - A segment may contain multiple citations if needed.
# - Do NOT include any claim unless you can provide supporting citations.
# - Keep the wording of the segment close to the cited evidence.
# """

system_prompt = f"""
You are a helpful assistant that answers user questions using the provided context documents.

Instructions:
- DATA FIDELITY: Your answer must be strictly faithful to the provided context documents, which are the text stated in the <CONTEXT DOCUMENTS></CONTEXT DOCUMENTS> tag and the attached images or files if exist.
- Do NOT use external knowledge, assumptions, implications, or hallucinated facts.
- If the context does not contain enough information to answer the question, return an empty array.
- Be concise and precise.

Output format:
Return a JSON array. Each item represents one segment of the final answer.

Each segment has three fields:
- "role": how this segment should be rendered when concatenated. Must be one of:
    - "sentence"      → append directly after previous segment (separated by a space)
    - "paragraph"     → start a new paragraph (insert blank line before this segment)
    - "bullet"        → render as a bullet point (prefix with "- ")
    - "bullet_intro"  → the sentence that introduces a bullet list (followed by ":")
- "segment": the text content of this segment (one factual claim)
- "citations": list of verbatim supporting strings from the <CONTEXT DOCUMENTS></CONTEXT DOCUMENTS> tag. If the answer is derived from an image, you MUST return its image_id in citations.

Format:
[
    {{
        "role": "sentence" | "paragraph" | "bullet" | "bullet_intro",
        "segment": "one factual claim",
        "citations": [
            {{ 
                "type": "source_text",
                "content":"exact verbatim supporting text from the context" 
            }},
            {{ 
                "type": "img",
                "img_id": id of the image
            }}
            
        ]
    }}
]

CITATION RULES:
- Every citation must be a VERBATIM substring of the provided context documents provided (the text inside <CONTEXT DOCUMENTS></CONTEXT DOCUMENTS> or the attached images).
  Before including a citation, verify that you can locate it word-for-word in the
  provided context. If you cannot find the exact text, do NOT include it.
- Citations must NOT be paraphrased, modified, truncated, or shortened (e.g., using "...")
- Each citation must be a complete sentence or phrase from the original text.
- If a segment cannot be supported by a verifiable verbatim citation, omit the segment
  entirely rather than fabricating a citation.
"""

# def build_prompt(query, context):
#     return f"""
#         ### SYSTEM INSTRUCTION ###
#         {prompt_str}
        
#         ### CONTEXT ###
#         {context}

#         ### USER QUESTION ###
#         {query}

#         ### ANSWER ###:
#         """

def build_prompt(query, context):
    return f"""
        <CONTEXT DOCUMENTS>
        {context}
        </CONTEXT DOCUMENTS>

        ### USER QUESTION ###
        {query}

        ### ANSWER ###: 
        """
        
llm = get_llm(LLM_PROVIDER) 
def generate_answer(query, docs):
    # docs đưa vô hàm này là phải được chốt rồi
    context_text, images = build_context(docs)
    prompt = build_prompt(query, context_text)

    images = images[:MAX_IMAGES_PER_LLMCALL]

    answer = llm.generate(system_prompt, prompt, images)

    return answer, context_text