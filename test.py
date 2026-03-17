import re

import chromadb
from openai import OpenAI
import os
from dotenv import load_dotenv

from pipeline_config import EMBEDDING_PROVIDER
from used_models.embeddings.embed_factory import EmbeddingService

from src.PIPELINE._1_ingest.ingest import file_path
load_dotenv()

# client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# res = client.embeddings.create(
#     model="text-embedding-3-small",
#     input="hello world"
# )

# print(res.data[0].embedding[:5])
# embedder = EmbeddingService(provider=EMBEDDING_PROVIDER)
# filename = os.path.basename(file_path)
# filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
# client = chromadb.Client()
# collection = client.get_or_create_collection(name=filename)

# query = "what is good software"

# query_emb = embedder.embed(query)

# results = collection.query(
#     query_embeddings=query_emb,
#     n_results=3
# )

# print(results)

print(len("haha"))