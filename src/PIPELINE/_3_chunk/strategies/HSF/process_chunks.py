import json
import os
import re

from PIPELINE._3_chunk.strategies.HSF.process_helpers.handle_batch import is_text_incomplete
from PIPELINE._3_chunk.strategies.HSF.process_helpers.normalize import is_heading_match
from pipeline_config import CHUNK_MAX_TOKEN

def get_all_gold_unit(node):
    gold_units = list(node.get("gold_unit", []))
    for child in node.get("children", []):
        gold_units.extend(get_all_gold_unit(child))
    return list(dict.fromkeys(gold_units))

def load_atomic_content(cursor, ids):
    placeholders = ",".join(["?"] * len(ids))
    cursor.execute(f"""
        SELECT *
        FROM atomic_elements
        WHERE id IN ({placeholders})
        ORDER BY atomic_order
    """, ids)
    return cursor.fetchall()


# def chunk_from_whole_node(node, cursor, file_path):
#     node_gold_units = get_all_gold_unit(node)
#     atomics = load_atomic_content(cursor, node_gold_units)
    
#     chunk_obj = {}
#     chunk_obj["metadata"] = {}
#     chunk_obj["content"] = {}

#     reconstructed_text = ""
    
#     is_incomplete_text = False
    
#     if "img" not in chunk_obj["content"]:
#         chunk_obj["content"]["img"] = []
        
#     for i in range(len(atomics)):
#         # print(atomic)
#         # return
#         atomic = atomics[i]
        
#         next_atomic = atomics[i+1]
#         next_is_main_heading = False
#         if next_atomic:
#             next_type = next_atomic["type"]
#             if next_type == "section_header":
#                 if atomic["heading_type"] == "main":
#                     next_is_main_heading = True
                    
                    
#         if atomic["type"] == "text":
#             text_content = atomic["content"]
            
#             if is_incomplete_text:
#                 reconstructed_text += f" {text_content}"
#             else:
#                 reconstructed_text += f"\n{text_content}"    
            
#             if is_text_incomplete(text_content):
#                 is_incomplete_text = True
#             else:
#                 is_incomplete_text = False  
                        
#         elif atomic["type"] == "section_header":
            
#             if atomic["heading_type"]== "nottoc" or atomic["heading_type"]== "nottoc":
#                 text_content = atomic["content"]
#                 reconstructed_text += f"\n\n### {text_content}"
#             elif atomic["heading_type"]== "main":
#                 text_content = atomic["content"]

#                 # nếu tiếp theo ko còn main heading, lấy path của nó để đánh dấu section
#                 if not next_is_main_heading:
#                     if reconstructed_text == "":
#                         reconstructed_text += f"# {atomic["description"]}"
#                     else:
#                         reconstructed_text += f"\n\n# {atomic["description"]}"
#                 # nếu vẫn còn main heading liền kề sau nó, đơn giản là skip nó        
            
#             is_incomplete_text = False  
        
#         elif atomic["type"] == "picture":
#             chunk_obj["content"]["img"].append(atomic["content"])
#             is_incomplete_text = False 
#         else:
#             content = atomic["content"]
#             if content:
#                 reconstructed_text += f"\n{content}"    
#             is_incomplete_text = False     
             
#     first_atomic = atomics[0]["atomic_order"]
#     # print(first_atomic)
#     # return
#     last_atomic = atomics[-1]["atomic_order"]
    
#     filename = os.path.basename(file_path)
#     filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
#     chunk_id = f"{filename}__chunk_{first_atomic}_{last_atomic}"
#     chunk_obj["content"]["text"] = reconstructed_text
#     chunk_obj["id"] = chunk_id
#     chunk_obj["metadata"]["document"] = filename
#     chunk_obj["metadata"]["token_count"] = node["token_count"]
#     chunk_obj["metadata"]["section"] = node["metadata"]["description"]
    
#     with open("chunk_test.json", "w", encoding="utf-8") as f:
#         json.dump(chunk_obj, f, ensure_ascii=False, default=str, indent=2)
#     return chunk_obj
            
def chunk_from_atomics(atomics, file_path, sum_token, base_path):
    # node_gold_units = get_all_gold_unit(node)
    # atomics = load_atomic_content(cursor, node_gold_units)
    
    chunk_obj = {}
    chunk_obj["metadata"] = {}
    chunk_obj["content"] = {}

    reconstructed_text = ""
    
    is_incomplete_text = False
    
    if "img" not in chunk_obj["content"]:
        chunk_obj["content"]["img"] = []
        
    for i in range(len(atomics)):
        # print(atomic)
        # return
        atomic = atomics[i]
        
        next_atomic = dict(atomics[i + 1]) if i + 1 < len(atomics) else None
        next_is_main_heading = False
        if next_atomic:
            next_type = next_atomic.get("type") 
            next_heading_type = next_atomic.get("heading_type")
            
            if next_type == "section_header" and next_heading_type == "main":
                next_is_main_heading = True                    
                    
        if atomic["type"] == "text":
            text_content = atomic["content"]
            
            if is_incomplete_text:
                reconstructed_text += f" {text_content}"
            else:
                reconstructed_text += f"\n{text_content}"    
            
            if is_text_incomplete(text_content):
                is_incomplete_text = True
            else:
                is_incomplete_text = False  
                        
        elif atomic["type"] == "section_header":
            
            if atomic["heading_type"]== "nottoc" or atomic["heading_type"]== "nottoc":
                text_content = atomic["content"]
                reconstructed_text += f"\n\n{text_content}"
            elif atomic["heading_type"]== "main":
                text_content = atomic["content"]

                # nếu tiếp theo ko còn main heading, lấy path của nó để đánh dấu section
                if not next_is_main_heading:
                    if reconstructed_text == "":
                        reconstructed_text += f"# {atomic["description"]}"
                    else:
                        reconstructed_text += f"\n\n# {atomic["description"]}"
                # nếu vẫn còn main heading liền kề sau nó, đơn giản là skip nó        
            
            is_incomplete_text = False  
        
        elif atomic["type"] == "picture":
            chunk_obj["content"]["img"].append(atomic["content"])
            is_incomplete_text = False 
        else:
            content = atomic["content"]
            if content:
                reconstructed_text += f"\n{content}"    
            is_incomplete_text = False     
             
    first_atomic = atomics[0]["atomic_order"]
    # print(first_atomic)
    # return
    last_atomic = atomics[-1]["atomic_order"]
    
    filename = os.path.basename(file_path)
    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    chunk_id = f"{filename}__chunk_{first_atomic}_{last_atomic}"
    chunk_obj["content"]["text"] = reconstructed_text
    chunk_obj["id"] = chunk_id
    chunk_obj["metadata"]["document"] = filename
    chunk_obj["metadata"]["token_count"] = sum_token
    chunk_obj["metadata"]["section"] = base_path
    
    with open("chunk_nottoc_test.json", "a", encoding="utf-8") as f:
        json.dump(chunk_obj, f, ensure_ascii=False, default=str, indent=2)
    return chunk_obj
                

def split_by_nottoc(atomics):   
    # trả về một blocks, mỗi phần tử là một nhóm các atomics sẽ được gộp vào một chunk
    blocks = []
    current = []
    
    for atomic in atomics:
        if atomic["type"] == "section_header" and atomic["heading_type"] == "nottoc":
            if current:
                blocks.append(current)
                current = []
            current.append(atomic)
        
        else:
            current.append(atomic)  
    
    if current:
        blocks.append(current)
    
    return blocks            
        

def create_chunk(node, cursor, file_path):
    node_gold_units = get_all_gold_unit(node)
    atomics = load_atomic_content(cursor, node_gold_units)
    
    base_path = node["metadata"]["description"]
    
    if node["token_count"] <= CHUNK_MAX_TOKEN:
        sum_token = node["token_count"]
        chunk = chunk_from_atomics(atomics=atomics, sum_token=sum_token, base_path=base_path)
        return [chunk]
    
    
    # bigger than max token, 1: split by nottoc heading
    blocks = split_by_nottoc(atomics)
    print("CHUNK BY NOTTOC")
    print([[dict(row) for row in block] for block in blocks])
    for block in blocks:
        # tính token
        block_token = sum(row["token_count"] for row in block)
        # nếu token thỏa thì chunk hết từ atomics của block này
        block_path = block[0]["description"]  # assume element đầu tiên là subheadding 
        chunk = chunk_from_atomics(block, file_path, block_token, block_path)
        
        # nếu không thì gọi hàm chunk nhỏ hơn
    
def build_chunks(node, file_path, cursor): # start from the root of the hierarchy tree
    chunks = []
    if (node["token_count"]<=CHUNK_MAX_TOKEN):
        create_chunk(node=node, cursor=cursor, file_path=file_path)
    else:
        if hasattr(node, "children") and node.children:  
            for child in node.children:
                chunks.append(build_chunks(child, file_path, cursor))  
    return chunks    
        
    