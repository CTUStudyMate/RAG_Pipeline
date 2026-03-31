from sentence_transformers import CrossEncoder

class CrossEncoderService:
    def __init__(self, model_name="cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model = CrossEncoder(model_name)

    def rerank(self, query, docs):
        pairs = [(query, doc["text"]) for doc in docs]
        scores = self.model.predict(pairs)

        for doc, score in zip(docs, scores):
            doc["rerank_score"] = float(score)

        return sorted(docs, key=lambda x: x["rerank_score"], reverse=True)