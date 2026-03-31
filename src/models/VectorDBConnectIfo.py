from dataclasses import dataclass

@dataclass
class VectorDBConnectIfo:
    db_path: str
    collection: str