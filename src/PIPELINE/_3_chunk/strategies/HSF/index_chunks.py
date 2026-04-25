
import chromadb
from pipeline_config import EMBEDDING_PROVIDER, FINAL_CHUNKS_TEST_FILEPATH, VECTOR_DB_HSF_PATH
from used_models.embeddings.embed_factory import EmbeddingService 
import psycopg
import json

def embed_content(texts, embedder):
    return embedder.embed(texts)


import psycopg
import json

def index_to_pgdb(pgdb_connect_info, chunk_ids, chunk_text_contents, chunk_metadatas):
    conn = psycopg.connect(
        host=pgdb_connect_info["host"],
        port=pgdb_connect_info["port"],
        dbname=pgdb_connect_info["db_name"],
        user=pgdb_connect_info["user"],
        password=pgdb_connect_info["password"]
    )
    
    cur = conn.cursor()
    table_name = pgdb_connect_info["table_name"]

    if not (len(chunk_ids) == len(chunk_text_contents) == len(chunk_metadatas)):
        raise ValueError("Input lists must have same length")

    data = [
        (doc_id, text, json.dumps(meta))
        for doc_id, text, meta in zip(chunk_ids, chunk_text_contents, chunk_metadatas)
    ]

    cur.executemany(
        f"""
        INSERT INTO {table_name} (document_id, text_content, metadata)
        VALUES (%s, %s, %s)
        ON CONFLICT (document_id) DO NOTHING
        """,
        data
    )

    conn.commit()
    cur.close()
    conn.close()
    
    

def build_index_data(chunks):
    embedder = EmbeddingService(provider=EMBEDDING_PROVIDER)
    documents = []
    metadatas = []
    ids = []
    
    texts = []
    
    for i, chunk in enumerate(chunks):
        chunk_text = chunk["content"]["text"]
        chunk_section = chunk["metadata"]["section"]
        
        #xử lý chunk_document
        chunk_document = chunk["metadata"]["document_path"]
        chunk_document = chunk_document.split(" > ")[-1]
            
        if chunk_section == " > " or chunk_section == "":
            chunk_section = "General"
        while chunk_section.startswith(" > "):
            chunk_section = chunk_section[3:]
        chunk_section = chunk_section.strip()
        
        store_text = f"[SECTION]: {chunk_section}\n[CONTENT]: {chunk_text}"
                 
        documents.append(store_text)
        
        metadata = {
        "document": chunk["metadata"]["document"],
        "section": chunk_section,
        "token_count": chunk["metadata"]["token_count"],
        "chunk_id": chunk["id"],
        }
        
        img = chunk["content"]["img"]
        if img:  # chỉ add khi có ảnh
            metadata["image"] = img
            
        metadatas.append(metadata)
    
        ids.append(f"{chunk['id']}_{i}")
        texts.append(store_text)
    
    embeddings = embed_content(texts, embedder)
    
    return ids, embeddings, documents, metadatas

def get_chroma_collection(collection_name, collection_path=VECTOR_DB_HSF_PATH):
    client = chromadb.PersistentClient(path=collection_path)
    collection = client.get_or_create_collection(name=collection_name, metadata={"hnsw:space": "cosine"})
    return collection, client

def index_to_chroma(collection, ids, embeddings, documents, metadatas, client):
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas
    )
    
    
def index_chunks(collection_name, chunks, pgdb_connect_info):
    ids, embeddings, documents, metadatas = build_index_data(chunks)
    
    collection, client = get_chroma_collection(collection_name)
    index_to_chroma(collection=collection, ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas, client=client)   
    
    index_to_pgdb(pgdb_connect_info=pgdb_connect_info, chunk_ids=ids, chunk_text_contents=documents, chunk_metadatas=metadatas)
    
    data = []

    for _id, doc, meta in zip(ids, documents, metadatas):
        data.append({
            "id": _id,
            "document": doc,
            "metadata": meta
        })
    with open(FINAL_CHUNKS_TEST_FILEPATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)