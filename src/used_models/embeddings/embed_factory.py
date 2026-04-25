
from used_models.embeddings.bge_embedding import BGEEmbedding
from used_models.embeddings.open_ai_embedding import OpenAIEmbedding

class EmbeddingService:
    def __init__(self, provider="openai", **kwargs):
        if provider == "bge":
            self.engine = BGEEmbedding(**kwargs)
            
        elif provider == "openai":
            self.engine = OpenAIEmbedding(**kwargs)

        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def embed(self, texts):
        return self.engine.embed(texts)