from PIPELINE._3_chunk.strategies.HSF.index_chunks import embed_content, get_chroma_collection, index_to_chroma, index_to_pgdb
from pipeline_config import EMBEDDING_PROVIDER, PGDB_CONNECT_INFO, VECTOR_DB_COLLECTION
from used_models.embeddings.embed_factory import EmbeddingService

embedder = EmbeddingService(provider=EMBEDDING_PROVIDER)
def index_chunks(collection_name, pgdb_connect_info):
    ids = ['c1', 'c2', 'c3', 'c4', 'c5', 'c6', 'c7']
    
    documents = ['a good software hahaha', 
                'a lazy worker is sleeping on the table', 
                'A software is considered useful when it can help user achieve their goals.', 
                'A slothful worker often doesn finish his work.', 
                'Machine learning models can improve performance with more data.',
                'Apple Inc. is an American multinational technology company headquartered in Cupertino',
                'A food company is located in this village.']
    
    embeddings = embed_content(embedder=embedder, texts=documents)
    metadatas = [{"document":"Example 1"}, {"document":"Example 2"}, {"document":"Example 3"}, {"document":"Example 4"}, {"document":"Example 5"}, {"document":"Example 6"}, {"document":"Example 7"}]
    
    collection, client = get_chroma_collection(collection_name, collection_path="data_test/chroma/hsf")
    index_to_chroma(collection=collection, ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas, client=client)   
    index_to_pgdb(pgdb_connect_info=pgdb_connect_info, chunk_ids=ids, chunk_text_contents=documents, chunk_metadatas=metadatas)
    
index_chunks(VECTOR_DB_COLLECTION, PGDB_CONNECT_INFO)  


  