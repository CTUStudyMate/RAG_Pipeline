import copy
import sqlite3

from PIPELINE._3_chunk.strategies.HSF.atomic_db_helpers.db_helpers import connect_db
from PIPELINE._3_chunk.strategies.HSF.hierarchy_helpers.DFSCursor import DFSCursor
from PIPELINE._3_chunk.strategies.HSF.process_chunks import build_chunks, create_chunk
from src.PIPELINE._3_chunk.strategies.HSF.process_token import compute_tree_token
from src.PIPELINE._3_chunk.strategies.HSF.process_atomics import process_atomics
import json
from src.PIPELINE._1_ingest.ingest import file_path

def HSF_chunk(file_path):
    hierarchy_tree2, conn = process_atomics(file_path)
    # #test-----------
    # with open("se_theory_practice_test_tree.json", "r", encoding="utf-8") as f:
    #     hierarchy_tree2 = json.load(f)
    #     # print(hierarchy_tree)
    # #---------------
    hierarchy_tree = copy.deepcopy(hierarchy_tree2)       
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    compute_tree_token(hierarchy_tree, cursor)
    
    cs = DFSCursor(hierarchy_tree)
    for i in range(0,8):
        cs.next()
    cs = cs.next()    
    print(cs["title"])
    
    create_chunk(node=cs, file_path=file_path, cursor=cursor)
    conn.close()

HSF_chunk(file_path)