import os
import re
import time

from PIPELINE._3_chunk.strategies.fixed_size.fixed_size_index import fixed_size_index_chunks
from PIPELINE._3_chunk.strategies.fixed_size.fixed_size_split_document import fixed_size_document_split
from common_utils.filename_handle import normalize_filename
from pipeline_config import settings
FIXEDSIZE_CHUNKING_TIME_LOG_FILE = settings.config["chunking_time_log_file"]
VECTOR_DB_FIXEDSIZE_COLLECTION = settings.config["vectordb_connect_info"]["collection"]
from src.PIPELINE._1_ingest.ingest import file_path


def fixed_size_chunk(file_path):
    doc_name = normalize_filename(file_path)
    doc_cache_dir = f"./data/parsed_cache/{doc_name}"
    texts = fixed_size_document_split(doc_cache_dir)
    # filename = os.path.basename(file_path)
    # filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    fixed_size_index_chunks(file_path=file_path, chunks=texts)
   
start = time.perf_counter()    
fixed_size_chunk(file_path=file_path)
end = time.perf_counter()
elapsed = end - start

with open(FIXEDSIZE_CHUNKING_TIME_LOG_FILE, "a", encoding="utf-8") as f:
    f.write(f"{file_path} | {elapsed:.2f} seconds\n")    