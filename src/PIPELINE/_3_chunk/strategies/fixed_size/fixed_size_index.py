import json
import os
import re

import chromadb

from PIPELINE._3_chunk.strategies.HSF.index_chunks import embed_content, index_to_chroma, index_to_pgdb
from PIPELINE._3_chunk.strategies.HSF.process_helpers.normalize import normalize_docname
import psycopg
from pipeline_config import settings
from used_models.embeddings.embed_factory import EmbeddingService
from PIPELINE._3_chunk.common_utils import mannual_token_count
from pipeline_setup import pool

EMBEDDING_PROVIDER = settings.config["embedding_provider"]
PGDB_FIXED_SIZE_CONNECT_INFO = settings.pgdb_connect_info
VECTOR_DB_FIXEDSIZE_INFO = settings.config["vectordb_connect_info"]

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
            "document": "1",
            "token_count": token,
            "chunk_id": chunk_id,
            "embeded_content": chunk_text #fixed size thì không có mô tả ảnh nên nội dung embed chính là phần source text luôn
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

    return ids, embeddings, documents, metadatas


_default_db_path = VECTOR_DB_FIXEDSIZE_INFO["db_path"]
_default_collection_name = VECTOR_DB_FIXEDSIZE_INFO["collection"]
_default_client = chromadb.PersistentClient(path=_default_db_path)
_default_collection = _default_client.get_or_create_collection(
    name=_default_collection_name,
    metadata={"hnsw:space": "cosine"}
)

def fixed_size_index_chunks(file_path, chunks, pgdb_connect_info=None, vectordb_connect_info=None):
    
    filename = os.path.basename(file_path)
    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    
    if vectordb_connect_info is None:
        client = _default_client
        collection = _default_collection
    else:
        client = chromadb.PersistentClient(
            path=vectordb_connect_info["db_path"]
        )
        collection = client.get_or_create_collection(
            name=vectordb_connect_info["collection"],
            metadata={"hnsw:space": "cosine"}
        )
    ids, embeddings, documents, metadatas = build_fixed_size_index_data(filename=filename, texts=chunks)
    
    index_to_chroma(collection=collection, ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas, client=client)  
    
    if pgdb_connect_info is None:
        pgdb_connect_info = PGDB_FIXED_SIZE_CONNECT_INFO 
    
    with pool.connection() as conn:
        with conn.cursor() as cur:
            index_to_pgdb(
                pgdb_connect_info=pgdb_connect_info,
                chunk_ids=ids,
                chunk_text_contents=documents,
                chunk_text_search_contents=documents,
                chunk_metadatas=metadatas,
                cur=cur
            )

            conn.commit()

        
    data = []

    for _id, doc, embed, meta in zip(ids, documents, documents, metadatas):
        data.append({
            "id": _id,
            "document": doc,
            "embeded_content": embed, # trong chroma db thì trường này nhét vào metadata luôn
            "metadata": meta
        })
    with open(settings.config["final_chunks_test_filepath"], "a", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)    
        f.write("\n")
