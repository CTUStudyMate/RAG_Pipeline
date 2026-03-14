import os
import json
from collections import deque
from pathlib import Path
from PIPELINE._3_chunk.strategies.HSF.atomic_db_helpers.db_helpers import create_db_for_document, insert_atomic_into_db
from PIPELINE._3_chunk.strategies.HSF.process_helpers.handle_batch import handle_batch_result
from common_utils.filename_handle import normalize_filename
from src.PIPELINE._3_chunk.strategies.HSF.hierarchy_helpers.build_hierarchy import build_hierarchy
from src.PIPELINE._3_chunk.strategies.HSF.hierarchy_helpers.DFSCursor import DFSCursor
from docling_core.types.doc.document import DoclingDocument


from src.PIPELINE._1_ingest.ingest import file_path

def flatten_node(node):
    """
    Flatten recursively a Docling node.
    """
    # Nếu node có children → flatten từng child
    if hasattr(node, "children") and node.children:
        result = []
        for child in node.children:
            result.extend(flatten_node(child))
        return result

    # Nếu là leaf node (text, table, picture...)
    return [node]

def flatten_body(document):
    flat_list = []

    for child in document.body.children:
        flat_list.extend(flatten_node(child))

    return flat_list


def flat_batch_result(batch_document):
    batch_elements = flatten_body(batch_document)
    return batch_elements


def parse_pdf_into_atomic_units(folder, hierarchy_tree, conn, passed_cursor, open_node, node):
    stream_elements = deque()
    
    current_atomic_order = 0
    incomplete_atomic = False

    folder = Path(folder)
    
    doc_db_cursor = conn.cursor()
    
    for json_file in sorted(folder.glob("*.json")):
        with open(json_file, "r", encoding="utf-8") as f:
            doc_dict = json.load(f)
            batch_document = DoclingDocument.model_validate(doc_dict)
            # print(json_file)
            flat_list = flat_batch_result(batch_document) # đã lấy ra được doc của mỗi batch ròi nè

        # ===== với mỗi doc tương ứng từng batch thì gọi hàm xử lý batch để làm các task trên =====
        # bắt đầu xem và sửa lại hàm handle batch result
            current_atomic_order, incomplete_atomic, passed_cursor, open_node, node = handle_batch_result(flat_list=flat_list, my_built_dfs=hierarchy_tree, batch_result=batch_document, stream_elements=stream_elements, current_atomic_order=current_atomic_order, incomplete_atomic=incomplete_atomic, doc_db_cursor=doc_db_cursor, conn2=conn, passed_cursor=passed_cursor, open_node=open_node, node=node)

    # loop xong hết qua các batch, add các element cuối cùng trong stream vào db 
    while len(stream_elements) > 0:
        element = stream_elements.popleft()   # O(1)
        
        #====Test streams element =======
        docname = "the_last_se"
        target_file = f"{docname}_streams.json"
        with open(target_file, "a", encoding="utf-8") as f:
            json.dump(element, f, ensure_ascii=False, default=str)
            f.write("\n")
        #===================================
        
        insert_atomic_into_db(element, doc_db_cursor)
        conn.commit()

def process_atomics (file_path: str):
    # phải đi qua hết các batch để giữ được link giữa các batch
    # hàm này chạy xong là có được các atomic elements (gold_units) 
    # đã lưu vào db để tiện sau đó lấy ra add vào chunk
    # và chạy xong là cũng có được một cây dfs với mỗi node chứa các gold_units của nó
    
    # cuối cùng cần dùng các atomic để hình thành chunk => cần return đường dẫn db lưu atomic 
    # cần return cây hierarchy
    
    conn = create_db_for_document(file_path)
    conn.commit()
    
    hierarchy_tree = build_hierarchy(file_path)
    # print(hierarchy_tree)
    # with open("test_tree.json", "w", encoding="utf-8") as f:
    #     json.dump(hierarchy_tree, f, ensure_ascii=False, indent=4)
    
    passed_cursor = DFSCursor(hierarchy_tree)
    open_node = passed_cursor.next() # point to ROOT
    node = passed_cursor.peek() # point to the first children
    
    while node and node["title"] == "cover": # skip cover page
        open_node = passed_cursor.next()
        node = passed_cursor.peek()
    
    doc_name = normalize_filename(file_path)
    doc_cache_dir = f"./data/parsed_cache/{doc_name}"
    
    parse_pdf_into_atomic_units(folder=doc_cache_dir,hierarchy_tree=hierarchy_tree, conn=conn, passed_cursor=passed_cursor, open_node=open_node, node=node)   
    
    
process_atomics(file_path)    
    
    