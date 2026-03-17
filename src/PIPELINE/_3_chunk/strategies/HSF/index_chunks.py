
import os
from openai import OpenAI
import chromadb
from pipeline_config import EMBEDDING_PROVIDER
from used_models.embeddings.embed_factory import EmbeddingService 

def embed_content(texts, embedder):
    return embedder.embed(texts)

def build_index_data(chunks):
    embedder = EmbeddingService(provider=EMBEDDING_PROVIDER)
    documents = []
    metadatas = []
    ids = []
    
    texts = []
    
    for i, chunk in enumerate(chunks):
        chunk_text = chunk["content"]["text"]
        chunk_section = chunk["metadata"]["section"]
        
        store_text = f"""
        [SECTION]: {chunk_section}
        [CONTENT]: {chunk_text}
        """
        
        documents.append(store_text)
        
        metadatas.append({
            "document": chunk["metadata"]["document"],
            "section": chunk_section,
            "token_count": chunk["metadata"]["token_count"],
            "chunk_id": chunk["id"],
        })
        img = chunk["content"]["img"]
        if img:  # chỉ add khi có ảnh
             metadatas["image"] = img
        ids.append(f"{chunk['id']}_{i}")
        texts.append(store_text)
    
    embeddings = embed_content(texts, embedder)
    
    return ids, embeddings, documents, metadatas

def get_chroma_collection(collection_name):
    client = chromadb.Client(
        settings=chromadb.config.Settings(
            persist_directory="./chroma_db"
        )
    )
    collection = client.get_or_create_collection(name=collection_name)
    return collection, client

def index_to_chroma(collection, ids, embeddings, documents, metadatas, client):
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas
    )
    client.persist()
    
    
def index_chunks(collection_name, chunks):
     ids, embeddings, documents, metadatas = build_index_data(chunks)
     collection, client = get_chroma_collection(collection_name)
     index_to_chroma(collection=collection, ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas, client=client)   