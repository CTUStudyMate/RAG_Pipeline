from typing import TypedDict

class NormalizedChunk(TypedDict):
    doc_id: str
    text: str
    metadata: dict
    score: float