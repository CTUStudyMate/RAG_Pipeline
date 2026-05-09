import json
import time

from langchain_docling.loader import DoclingLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from pipeline_config import CHUNKING_TIME_LC_BASED_LOG_FILE

FILE_PATH = "./docs/se_theory_practice.pdf"

start = time.perf_counter()
splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=80)

loader = DoclingLoader(file_path=FILE_PATH)
doc_iter = loader.lazy_load()

all_split_docs = []

global_chunk_id = 0

for doc in doc_iter:
    if not doc.page_content.strip():
        continue

    split_docs = splitter.split_documents([doc])

    for split_doc in split_docs:
        split_doc.metadata = {
            **split_doc.metadata,
            "chunk_id": global_chunk_id,
            "source": FILE_PATH
        }

        all_split_docs.append(split_doc)
        global_chunk_id += 1
end = time.perf_counter()
elapsed = end - start
with open(CHUNKING_TIME_LC_BASED_LOG_FILE, "w", encoding="utf-8") as f:
    f.write(f"{FILE_PATH} | {elapsed:.2f} seconds\n")

with open("./exp/langchain_based/exp_result_recusive_char_splitter/chunks.json") as f:
    json.dump(all_split_docs, f, indent=2)        