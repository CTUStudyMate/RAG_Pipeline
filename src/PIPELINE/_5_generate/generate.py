from openai import OpenAI


from common_utils.debug import log_to_file
from pipeline_config import LLM_PROVIDER, MAX_IMAGES_PER_LLMCALL
from src.used_models.llm.LLM_Factory import get_llm

# client = OpenAI()

def build_context(docs):
    context_parts = []
    images = []
    for i, doc in enumerate(docs, start=1):
        content = doc.get("text", "")
        metadata = doc.get("metadata", {})

        # text context
        context_parts.append(
            f"[{i}]\n"
            f"{content}\n"
        )

        if "image" in metadata and metadata["image"]:
            for img in metadata["image"]:
                images.append(img)

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

system_prompt = f"""
You are a helpful assistant that answers user questions using the provided context documents.

Instructions:
- DATA FIDELITY: Your answer must be strictly faithful to the provided context documents. Use ONLY information explicitly stated in the source text.
- Do NOT use any external knowledge or assumptions. Do NOT hallucinate.
- If the context does not contain enough information to answer the question, clearly say you don't have enough information to answer the question.
- Be concise but clear.

Citation rules:
- INLINE CITATIONS REQUIRED: Place citation markers IMMEDIATELY after the specific fact, entity, or claim they support. Do NOT wait until the end of the paragraph to cite.
- GRANULARITY: If a single sentence contains multiple distinct claims from different sources, you MUST insert citations mid-sentence directly after each claim (e.g., "Software engineering focuses on practical solutions [1], whereas computer science investigates theoretical algorithms [2].").
- STRICT PLACEMENT: Never group all citations at the end of a paragraph. A paragraph without internal/inline citations is considered a failure.
- Format the citation as [1], [2], etc. Place the citation just before commas or periods.
- Only cite when a fact is presented; do not cite common knowledge or transitional phrases.
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
        ### CONTEXT DOCUMENTS ###
        {context}

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