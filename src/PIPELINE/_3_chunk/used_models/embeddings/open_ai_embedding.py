from pipeline_config import OPENAI_EMBEDDING_MODEL
from src.PIPELINE._3_chunk.used_models.embeddings.base_embedding import BaseEmbedding
from openai import OpenAI

class OpenAIEmbedding(BaseEmbedding):
    def __init__(self, model=OPENAI_EMBEDDING_MODEL):
        self.client = OpenAI()
        self.model = model

    def embed(self, texts):
        if isinstance(texts, str):
            texts = [texts]

        response = self.client.embeddings.create(
            model=self.model,
            input=texts
        )

        return [item.embedding for item in response.data]