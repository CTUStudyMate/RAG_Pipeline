import json
from pathlib import Path
import time

from langchain_docling.loader import DoclingLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.PIPELINE._3_chunk.common_utils import mannual_token_count
from src.PIPELINE._3_chunk.strategies.HSF.index_chunks import embed_content, get_chroma_collection, index_chunks, index_to_chroma, index_to_pgdb
from common_utils.filename_handle import normalize_filename
from pipeline_config import CHUNKING_TIME_LC_BASED_LOG_FILE, EMBEDDING_PROVIDER, PGDB_LC_RECUR_CONNECT_INFO, VECTOR_DB_LC_RECUR_COLLECTION, VECTOR_DB_LC_RECUR_PATH, VECTORDB_LC_RECUR_CONNECT_INFO
from docling_core.types.doc.document import DoclingDocument
from langchain_core.documents import Document
from src.PIPELINE._1_ingest.ingest import file_path
from src.PIPELINE._3_chunk.strategies.HSF.process_helpers.normalize import normalize_docname
from src.used_models.embeddings.embed_factory import EmbeddingService



# def lc_recursive_charsplit_chunk():
#     FILE_PATH = "./docs/se_theory_practice.pdf"
#     filename = normalize_filename(FILE_PATH)

#     start = time.perf_counter()

#     splitter = RecursiveCharacterTextSplitter(
#         chunk_size=600,
#         chunk_overlap=80
#     )

#     loader = DoclingLoader(file_path=FILE_PATH)
#     doc_iter = loader.lazy_load()

#     all_split_docs = []
#     global_chunk_id = 0

#     for doc in doc_iter:
#         text = doc.page_content.strip()
#         if not text:
#             continue

#         split_docs = splitter.split_documents([doc])

#         for split_doc in split_docs:
#             split_doc.id = f"{str(global_chunk_id)}_{filename}"
#             split_doc.metadata = {
#                 **split_doc.metadata,
#                 "source": FILE_PATH
#             }

#             all_split_docs.append(split_doc)
#             global_chunk_id += 1

#     end = time.perf_counter()
#     elapsed = end - start

#     # log time
#     with open(CHUNKING_TIME_LC_BASED_LOG_FILE, "w", encoding="utf-8") as f:
#         f.write(f"{FILE_PATH} | {elapsed:.2f} seconds\n")

#     # convert sang JSON
#     json_docs = [
#         {
#             "id": doc.id,
#             "document": doc.page_content,
#             "metadata": doc.metadata
#         }
#         for doc in all_split_docs
#     ]

#     # này chỉ để check xem chunk nó nhìn như nào thôi
#     with open("./exp/langchain_based/exp_result_recusive_char_splitter/chunks.json", "w", encoding="utf-8") as f:
#         json.dump(json_docs, f, indent=2, ensure_ascii=False)
        
#     return json_docs

def index_lc_recur_chunks(chunks):
    ids = []
    documents = []
    metadatas = []
    for chunk in chunks:
        ids.append(chunk["id"])
        documents.append(chunk["document"])
        metadatas.append(chunk["metadata"])
        
    embedder = EmbeddingService(provider=EMBEDDING_PROVIDER)
    embeddings = embed_content(documents, embedder)
    
    collection, client = get_chroma_collection(collection_name=VECTOR_DB_LC_RECUR_COLLECTION, collection_path=VECTOR_DB_LC_RECUR_PATH)
    index_to_chroma(collection=collection, ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas, client=client)
    index_to_pgdb(pgdb_connect_info=PGDB_LC_RECUR_CONNECT_INFO, chunk_ids=ids, chunk_text_contents=documents, chunk_metadatas=metadatas)
    
def lc_recursive_charsplit_chunk(folder):
    splitter = RecursiveCharacterTextSplitter(chunk_size=2136, chunk_overlap=285)
    global_chunk_id = 0
    folder = Path(folder)
    file_name = normalize_filename(file_path=file_path)
    docname = normalize_docname(file_path)
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
                        "document": docname,
                        "token_count":token_count
                    }
                }
                all_chunks.append(chunk)
                global_chunk_id += 1
    
    index_lc_recur_chunks(all_chunks)
    end = time.perf_counter()
    elapsed = end - start 
    with open(CHUNKING_TIME_LC_BASED_LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"{file_path} | {elapsed:.2f} seconds\n") 
    with open("./exp/langchain_based/exp_result_recusive_char_splitter/chunks.json", "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, default=str, ensure_ascii=False)
    return all_chunks   
    
doc_name = normalize_filename(file_path)   
doc_cache_dir = f"./data/parsed_cache/{doc_name}"
lc_recursive_charsplit_chunk(doc_cache_dir)


        
        