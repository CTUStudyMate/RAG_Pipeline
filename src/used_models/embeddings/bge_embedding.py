import requests
from used_models.embeddings.base_embedding import BaseEmbedding

class BGEEmbedding(BaseEmbedding):
    def __init__(self, model="bge-m3:latest", base_url="http://localhost:11434"):
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