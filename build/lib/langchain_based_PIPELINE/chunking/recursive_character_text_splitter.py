import json
import time

from langchain_docling.loader import DoclingLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.PIPELINE._3_chunk.strategies.HSF.index_chunks import index_chunks
from common_utils.filename_handle import normalize_filename
from pipeline_config import CHUNKING_TIME_LC_BASED_LOG_FILE, PGDB_LC_RECUR_CONNECT_INFO, VECTORDB_LC_RECUR_CONNECT_INFO


def lc_recursive_charsplit_chunk():
    FILE_PATH = "./docs/se_theory_practice.pdf"
    filename = normalize_filename(FILE_PATH)

    start = time.perf_counter()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=80
    )

    loader = DoclingLoader(file_path=FILE_PATH)
    doc_iter = loader.lazy_load()

    all_split_docs = []
    global_chunk_id = 0

    for doc in doc_iter:
        text = doc.page_content.strip()
        if not text:
            continue

        split_docs = splitter.split_documents([doc])

        for split_doc in split_docs:
            split_doc.id = f"{str(global_chunk_id)}_{filename}"
            split_doc.metadata = {
                **split_doc.metadata,
                "source": FILE_PATH
            }

            all_split_docs.append(split_doc)
            global_chunk_id += 1

    end = time.perf_counter()
    elapsed = end - start

    # log time
    with open(CHUNKING_TIME_LC_BASED_LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"{FILE_PATH} | {elapsed:.2f} seconds\n")

    # convert sang JSON
    json_docs = [
        {
            "id": doc.id,
            "document": doc.page_content,
            "metadata": doc.metadata
        }
        for doc in all_split_docs
    ]

    # này chỉ để check xem chunk nó nhìn như nào thôi
    with open("./exp/langchain_based/exp_result_recusive_char_splitter/chunks.json", "w", encoding="utf-8") as f:
        json.dump(json_docs, f, indent=2, ensure_ascii=False)
        
    return json_docs

# vẫn lưu thành vector store và bm25 như mọi cái khác thôi
chunks = lc_recursive_charsplit_chunk()
index_chunks(chunks=chunks, collection_name=VECTORDB_LC_RECUR_CONNECT_INFO, pgdb_connect_info=PGDB_LC_RECUR_CONNECT_INFO)

        
        