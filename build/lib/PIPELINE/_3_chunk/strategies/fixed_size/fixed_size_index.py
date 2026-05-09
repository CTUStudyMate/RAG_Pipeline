import json
import os
import re

import chromadb

from PIPELINE._3_chunk.strategies.HSF.index_chunks import embed_content, index_to_chroma, index_to_pgdb
from PIPELINE._3_chunk.strategies.HSF.process_helpers.normalize import normalize_docname
from pipeline_config import EMBEDDING_PROVIDER, PGDB_FIXED_SIZE_CONNECT_INFO, VECTOR_DB_FIXEDSIZE_PATH
from used_models.embeddings.embed_factory import EmbeddingService
from PIPELINE._3_chunk.common_utils import mannual_token_count



def build_fixed_size_index_data(texts, filename):
    embedder = EmbeddingService(provider=EMBEDDING_PROVIDER)
    
    documents = []
    metadatas = []
    ids = []
    records = []  

    docname = normalize_docname(filename)

    for i, text in enumerate(texts):
        chunk_text = text.strip()
        if not chunk_text:
            continue

        chunk_id = f"{docname}_chunk_{i}"
        token = mannual_token_count(chunk_text)

        metadata = {
            "document": filename,
            "token_count": token,
            "chunk_id": chunk_id,
        }

        documents.append(chunk_text)
        metadatas.append(metadata)
        ids.append(chunk_id)

        records.append({
            "id": chunk_id,
            "text": chunk_text,
            "metadata": metadata
        })

    if not documents:
        print("No valid chunks to embed")
        return [], [], [], []

    embeddings = embed_content(documents, embedder)

    with open("fixed_size_chunks.json", "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    return ids, embeddings, documents, metadatas

def get_fs_chroma_collection(collection_name):
    client = chromadb.PersistentClient(path=VECTOR_DB_FIXEDSIZE_PATH)
    collection = client.get_or_create_collection(name=collection_name, metadata={"hnsw:space": "cosine"})
    return collection, client


def fixed_size_index_chunks(collection_name, chunks):
    ids, embeddings, documents, metadatas = build_fixed_size_index_data(filename=collection_name, texts=chunks)
    
    collection, client = get_fs_chroma_collection(collection_name)
    index_to_chroma(collection=collection, ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas, client=client)  
    index_to_pgdb(pgdb_connect_info=PGDB_FIXED_SIZE_CONNECT_INFO, chunk_ids=ids, chunk_text_contents=documents, chunk_metadatas=metadatas)
    