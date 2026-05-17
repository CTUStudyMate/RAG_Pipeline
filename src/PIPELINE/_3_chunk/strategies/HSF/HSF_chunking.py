import copy
import os
import re
import sqlite3
import time

from PIPELINE._3_chunk.strategies.HSF.atomic_db_helpers.db_helpers import connect_db
from PIPELINE._3_chunk.strategies.HSF.hierarchy_helpers.DFSCursor import DFSCursor
from PIPELINE._3_chunk.strategies.HSF.index_chunks import index_chunks
from PIPELINE._3_chunk.strategies.HSF.process_chunks import build_chunks, create_chunk
from pipeline_config import settings
from src.PIPELINE._3_chunk.strategies.HSF.process_token import compute_tree_token
from src.PIPELINE._3_chunk.strategies.HSF.process_atomics import process_atomics
import json
from src.PIPELINE._1_ingest.ingest import file_path, prefix_path

FINAL_CHUNKS_TEST_FILEPATH = settings.config["final_chunks_test_filepath"]
HSF_CHUNKING_TIME_LOG_FILE = settings.config["chunking_time_log_file"]
PGDB_HSF_CONNECT_INFO = settings.pgdb_connect_info
VECTOR_DB_HSF_COLLECTION = settings.config["vectordb_connect_info"]["collection"]

def HSF_chunk(file_path, prefix_path, pgdb_connect_info=PGDB_HSF_CONNECT_INFO):
    
    #1. Tạo cây hierarchy của document và xử lý các atomics parse được
    hierarchy_tree2, conn = process_atomics(file_path)
    #test-----------
    # with open("exp/se/tree.json", "r", encoding="utf-8") as f:
    #     hierarchy_tree2 = json.load(f)
        # print(hierarchy_tree)
    # #---------------
    
    hierarchy_tree = copy.deepcopy(hierarchy_tree2)       
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    #2. tính token để thực hiện chia chunk thỏa ngưỡng
    compute_tree_token(hierarchy_tree, cursor)
    
    cs = DFSCursor(hierarchy_tree)
    # for i in range (0,8):
    #     cs.next()
    cs = cs.next()    
    
    chunks = build_chunks(node=cs, file_path=file_path, cursor=cursor, prefix_path=prefix_path)
    
    conn.close()
    index_chunks(chunks=chunks, collection_name=VECTOR_DB_HSF_COLLECTION, pgdb_connect_info=pgdb_connect_info)



start = time.perf_counter()
HSF_chunk(file_path, prefix_path, pgdb_connect_info=PGDB_HSF_CONNECT_INFO)
end = time.perf_counter()
elapsed = end - start

with open(HSF_CHUNKING_TIME_LOG_FILE, "w", encoding="utf-8") as f:
    f.write(f"{file_path} | {elapsed:.2f} seconds\n")
# print("hahaha")