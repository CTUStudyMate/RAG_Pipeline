from openai import OpenAI

from PIPELINE._5_generate.LLM_Factory import get_llm
from common_utils.debug import log_to_file
from pipeline_config import LLM_PROVIDER, MAX_IMAGES_PER_LLMCALL
client = OpenAI()


def build_context(docs):
    context_parts = []
    images = []
    for i, doc in enumerate(docs, start=1):
        content = doc.get("text", "")
        metadata = doc.get("metadata", {})

        # text context
        context_parts.append(
            f"[CHUNK #{i}]\n"
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

prompt_str = f"""
You are a helpful assistant.

        Instructions:
        - Use ONLY the information provided from the context to answer the questions.
        - If the context doesn't provide enough information for you to answer, say you don't have enough information to answer the question.
        - Be concise but clear.
        - Do NOT hallucinate.
"""


def build_prompt(query, context):
    return f"""
        ### SYSTEM INSTRUCTION ###
        {prompt_str}
        
        ### CONTEXT ###
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

    answer = llm.generate(prompt, images)

    return answer, context_text