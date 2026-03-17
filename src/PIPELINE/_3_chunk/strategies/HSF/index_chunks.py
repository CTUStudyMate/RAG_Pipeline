def index_chunks(chunks):
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
        
        ids.append(f"{chunk['id']}_{i}")
        texts.append(store_text)
    
    embeddings = embed_content(texts)
    
    return ids, embeddings, documents, metadatas