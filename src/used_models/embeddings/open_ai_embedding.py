from pipeline_config import OPENAI_EMBEDDING_MODEL
from openai import OpenAI
from used_models.embeddings.base_embedding import BaseEmbedding
import os
from dotenv import load_dotenv
load_dotenv() 

class OpenAIEmbedding(BaseEmbedding):
    def __init__(self, model=OPENAI_EMBEDDING_MODEL):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model

    def embed(self, texts, batch_size=50, show_progress=True):
        if isinstance(texts, str):
            texts = [texts]

        all_embeddings = []
        total = len(texts)

        for i in range(0, total, batch_size):
            batch = texts[i:i + batch_size]

            if show_progress:
                print(f"[Embedding] Processing batch {i//batch_size + 1} / {(total - 1)//batch_size + 1}")

            response = self.client.embeddings.create(
                model=self.model,
                input=batch
            )

            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)

        return all_embeddings