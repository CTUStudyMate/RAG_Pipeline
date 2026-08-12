import json
import math
from pathlib import Path
import time
from pipeline_setup import pool

from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.PIPELINE._3_chunk.common_utils import mannual_token_count
from src.PIPELINE._3_chunk.strategies.HSF.index_chunks import embed_content, get_chroma_collection, index_chunks, index_to_chroma, index_to_pgdb
from common_utils.filename_handle import normalize_filename
from docling_core.types.doc.document import DoclingDocument
from langchain_core.documents import Document
from src.PIPELINE._1_ingest.ingest import file_path
from src.PIPELINE._3_chunk.strategies.HSF.process_helpers.normalize import normalize_docname
from src.used_models.embeddings.embed_factory import EmbeddingService

from pipeline_config import settings
CHUNKING_TIME_LC_BASED_LOG_FILE = settings.config["chunking_time_log_file"]
PGDB_LC_RECUR_CONNECT_INFO = settings.pgdb_connect_info
VECTOR_DB_LC_RECUR_COLLECTION = settings.config["vectordb_connect_info"]["collection"]

def index_lc_recur_chunks(chunks):
    ids = []
    documents = []
    metadatas = []
    for chunk in chunks:
        ids.append(chunk["id"])
        documents.append(chunk["document"])
        metadatas.append(chunk["metadata"])
        
    embedder = EmbeddingService(provider=settings.config["embedding_provider"])

    embeddings = embed_content(documents, embedder)
    
    collection, client = get_chroma_collection(collection_name=VECTOR_DB_LC_RECUR_COLLECTION)
    index_to_chroma(collection=collection, ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas, client=client)
    with pool.connection() as conn:
        with conn.cursor() as cur:
            index_to_pgdb(pgdb_connect_info=PGDB_LC_RECUR_CONNECT_INFO, chunk_ids=ids, chunk_text_contents=documents, chunk_metadatas=metadatas, chunk_text_search_contents=documents, cur=cur)
            conn.commit()

chunk_max_token = settings.config["chunk_max_token"]  
overlap_tokens = settings.config["overlap_tokens"]
chunk_size = math.ceil(chunk_max_token * 3.56)
overlap = math.ceil(overlap_tokens * 3.56)
def lc_recursive_charsplit_chunk(folder):
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=overlap)
    global_chunk_id = 0
    folder = Path(folder)
    file_name = normalize_filename(file_path=file_path)
    # docname = normalize_docname(file_path)
    json_files = sorted(folder.glob("*.json"))
    total_batches = len(json_files)
    
    all_chunks = []
    start = time.perf_counter()
    for i, json_file in enumerate(json_files, start=1):
        print(f"Processing batch {i}/{total_batches}: {json_file.name}")
        with open(json_file, "r", encoding="utf-8") as f:
            doc_dict = json.load(f)
            batch_document = DoclingDocument.model_validate(doc_dict)
            text = batch_document.export_to_markdown()
            doc = Document(
                page_content=text,
                metadata={
                    "source": str(json_file)
                }
            )
            split_docs = splitter.split_documents([doc])
            for split_doc in split_docs:
                token_count = mannual_token_count(split_doc.page_content)
                chunk = {
                    "id": f"{str(global_chunk_id)}_{file_name}",
                    "document": split_doc.page_content,
                    "metadata":{
                        "document": "1",
                        "token_count":token_count,
                        "embeded_content": split_doc.page_content
                    }
                }
                all_chunks.append(chunk)
                global_chunk_id += 1
    
    index_lc_recur_chunks(all_chunks)
    end = time.perf_counter()
    elapsed = end - start 
    with open(CHUNKING_TIME_LC_BASED_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{file_path} | {elapsed:.2f} seconds\n") 
    with open(settings.config["final_chunks_test_filepath"], "a", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, default=str, ensure_ascii=False)
        f.write("\n")
    return all_chunks   
    
doc_name = normalize_filename(file_path)   
doc_cache_dir = f"./data/parsed_cache/{doc_name}"

# lc_recursive_charsplit_chunk(doc_cache_dir)


        
        
