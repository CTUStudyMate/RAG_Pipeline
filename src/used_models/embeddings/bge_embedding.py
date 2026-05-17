import requests
from pipeline_config import settings
from used_models.embeddings.base_embedding import BaseEmbedding

BGE_EMBEDDING_MODEL = settings.config["bge_embedding_model"]
class BGEEmbedding(BaseEmbedding):
    def __init__(self, model=BGE_EMBEDDING_MODEL, base_url="http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    def embed(self, texts, batch_size=10):
        if isinstance(texts, str):
            texts = [texts]

        embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]

            response = requests.post(
                f"{self.base_url}/api/embed",
                json={
                    "model": self.model,
                    "input": batch
                }
            )

            if response.status_code != 200:
                raise Exception(f"Embedding error: {response.text}")

            data = response.json()
            embeddings.extend(data["embeddings"])

        return embeddings