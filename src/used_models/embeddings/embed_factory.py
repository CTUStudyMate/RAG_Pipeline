
from used_models.embeddings.bge_embedding import BGEEmbedding
from used_models.embeddings.open_ai_embedding import OpenAIEmbedding

class EmbeddingService:
    def __init__(self, provider="openai", **kwargs):
        if provider == "openai":
            self.engine = OpenAIEmbedding(**kwargs)
        
        elif provider == "bge":
            self.engine = BGEEmbedding(**kwargs)
        
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def embed(self, texts):
        return self.engine.embed(texts)