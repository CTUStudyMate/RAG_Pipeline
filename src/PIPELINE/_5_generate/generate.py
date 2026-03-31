from openai import OpenAI

from pipeline_config import MAX_IMAGES_PER_LLMCALL
client = OpenAI()


def build_context(docs):
    context_parts = []
    images = []

    for i, doc in enumerate(docs, start=1):
        content = doc.get("text", "")
        metadata = doc.get("metadata", {})

        # text context
        context_parts.append(
            f"[Chunk {i}]\n"
            f"{content}\n"
        )

        if "image" in metadata and metadata["image"]:
            for img in metadata["image"]:
                images.append(img)

    context_text = "\n".join(context_parts)
    return context_text, images



def build_prompt(query, context):
    context_text = context[0]
    return f"""
        You are a helpful assistant answering questions based ONLY on the provided context.

        Instructions:
        - Use ONLY the information from the context below
        - If the answer is not in the context, say you don't have enough information to answer the question
        - Be concise but clear
        - Do NOT hallucinate

        Context:
        {context_text}

        Question:
        {query}

        Answer:
        """
        
def generate_answer(query, docs):
    context_text, images = build_context(docs)
    prompt = build_prompt(query, context_text)

    images = images[:MAX_IMAGES_PER_LLMCALL]

    # build content dạng multimodal
    content = [{"type": "text", "text": prompt}]

    for img in images:
        content.append({
            "type": "image_url",
            "image_url": {
                "url": img  # base64 dạng data:image/png;base64,...
            }
        })

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "user",
                "content": content
            }
        ],
        temperature=0
    )

    return response.choices[0].message.content  