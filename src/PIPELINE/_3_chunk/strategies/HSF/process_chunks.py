import json
import os
import re

from PIPELINE._3_chunk.common_utils import mannual_token_count, split_text
from PIPELINE._3_chunk.strategies.HSF.process_helpers.handle_batch import is_text_incomplete
from PIPELINE._3_chunk.strategies.HSF.process_helpers.normalize import is_heading_match
from pipeline_config import CHUNK_FROM_ATOMIC_TEST_FILEPATH, CHUNK_MAX_TOKEN, CHUNK_MIN_TOKEN, IMAGE_TOKEN_ESTIMATE

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
            
            if atomic["heading_type"]== "nottoc":
                text_content = atomic["content"]
                reconstructed_text += f"\n\n{text_content}"
            elif atomic["heading_type"]== "main":

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
    
    # TEST CHUNK RESULT -------------------------------------------------
    # with open(CHUNK_FROM_ATOMIC_TEST_FILEPATH, "a", encoding="utf-8") as f:
    #     json.dump(chunk_obj, f, ensure_ascii=False, default=str, indent=2)
    # --------------------------------------------------------------
        
        
    return chunk_obj
                
def fixed_size_split(atomic, file_path, sum_token, base_path):
    ori_chunk = chunk_from_atomics([atomic], file_path, sum_token, base_path)

    if atomic["type"] == "text":
        chunks = []
        chunk_text = ori_chunk["content"]["text"]
        texts = split_text(chunk_text)

        for i, (text, token) in enumerate(texts):
            new_chunk = {
                "id": f"{ori_chunk['id']}_part_{i}",
                "metadata": {
                    **ori_chunk["metadata"],
                    "token_count": token
                },
                "content": {
                    "img": ori_chunk["content"]["img"],  # reuse (không đổi)
                    "text": text
                }
            }

            chunks.append(new_chunk)

        return chunks

    else:
        return [ori_chunk]  
    

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

def new_chunk(chunk_section_path, filename):
    chunk = {}
    chunk["metadata"] = {}
    chunk["content"] = {}

    chunk["metadata"]["document"] = filename
    chunk["metadata"]["token_count"] = 0
    chunk["metadata"]["section"] = chunk_section_path
    chunk["content"]["img"] = []
    chunk["content"]["text"] = ""
    chunk["id"] = "new_chunk_id"
    return chunk
    

def merge_atomic_to_chunk(current_chunk, atomic):
    is_incomplete_text = False
    chunk_text = current_chunk["content"]["text"] or ""
    if atomic["type"] == "text":
            text_content = atomic["content"]
            if is_incomplete_text:
                chunk_text += f" {text_content}"
            else:
                chunk_text += f"\n{text_content}" 
                   
            if is_text_incomplete(text_content):
                is_incomplete_text = True
            else:
                is_incomplete_text = False  
                        
    elif atomic["type"] == "section_header":
        if atomic["heading_type"]== "nottoc" or atomic["heading_type"]== "nottoc":
            text_content = atomic["content"]
            chunk_text += f"\n\n{text_content}"
        elif atomic["heading_type"]== "main":
            chunk_text += f"\n\n# {atomic["description"]}"
        
        is_incomplete_text = False  
    
    elif atomic["type"] == "picture":
        current_chunk["content"]["img"].append(atomic["content"])
        is_incomplete_text = False 
    else:
        content = atomic["content"]
        if content:
            chunk_text += f"\n{content}"    
        is_incomplete_text = False  
    
    chunk_token = mannual_token_count(text=chunk_text)
    chunk_token += len(current_chunk["content"]["img"])* IMAGE_TOKEN_ESTIMATE
    current_chunk["metadata"]["token_count"] = chunk_token
    
    
    return current_chunk
    
def merge_chunk_to_chunk(chunk1, chunk2):
    metadata = {
        **chunk1["metadata"]
    }

    text1 = chunk1["content"].get("text", "")
    text2 = chunk2["content"].get("text", "")

    merged_text = (text1.strip() + "\n\n" + text2.strip()).strip()

    imgs1 = chunk1["content"].get("img", [])
    imgs2 = chunk2["content"].get("img", [])

    merged_imgs = imgs1 + imgs2  # concat list

    metadata["token_count"] = (
        chunk1["metadata"].get("token_count", 0)
        + chunk2["metadata"].get("token_count", 0)
    )

    def extract_range(chunk_id):
        try:
            range_part = chunk_id.split("__chunk_")[-1]
            start, end = range_part.split("_")
            return start, end
        except:
            return None, None

    start1, _ = extract_range(chunk1["id"])
    _, end2 = extract_range(chunk2["id"])

    if start1 and end2:
        new_id = f"{chunk1['id'].split('__chunk_')[0]}__chunk_{start1}_{end2}"
    else:
        # fallback nếu format id không chuẩn
        new_id = f"{chunk1['id']}__merged__{chunk2['id']}"

    merged_chunk = {
        "id": new_id,
        "metadata": metadata,
        "content": {
            "img": merged_imgs,
            "text": merged_text
        }
    }
    return merged_chunk   
    
def chunk_by_semantic_units(atomics, chunk_section_path, file_path):
    chunks = []

    filename = os.path.basename(file_path)
    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)

    current_chunk = new_chunk(chunk_section_path, filename)

    first_atomic = atomics[0]["atomic_order"]
    last_atomic = atomics[0]["atomic_order"]

    def flush_chunk():
        nonlocal current_chunk, first_atomic, last_atomic

        chunk_id = f"{filename}__chunk_{first_atomic}_{last_atomic}"
        current_chunk["id"] = chunk_id
        chunks.append(current_chunk)

        current_chunk = new_chunk(chunk_section_path, filename)
        first_atomic = None
        last_atomic = None

    for atomic in atomics:

        if first_atomic is None:
            first_atomic = atomic["atomic_order"]

        if (current_chunk["metadata"]["token_count"] + atomic["token_count"] >= CHUNK_MAX_TOKEN):

            # nếu chunk hiện tại đã trên min token thì ok flush
            if current_chunk["metadata"]["token_count"] >= CHUNK_MIN_TOKEN:
                flush_chunk()
                current_chunk = merge_atomic_to_chunk(current_chunk=current_chunk, atomic=atomic)
                last_atomic = atomic["atomic_order"]
                continue

            else:
            # cộng chunk vô thì lớn hơn, nhưng chunk hiện tại dưới ngưỡng min token: 
                # nếu atomic dưới max_token, miễn cưỡng gộp chunk hiện tại vô
                if atomic["token_count"] < CHUNK_MAX_TOKEN:
                    current_chunk = merge_atomic_to_chunk(current_chunk=current_chunk, atomic=atomic)
                    last_atomic = atomic["atomic_order"]
                    flush_chunk()
                    continue

                # nếu atomic lớn hơn bằng max_token
                    # split atomic hiện tại với token < max_token - min_token (tại vì phải gộp với current chunk)
                    # rồi gộp chunk vào chunk đầu tiên của splitted list
                fixed_size_chunks = fixed_size_split(atomic, file_path, atomic["token_count"], chunk_section_path)

                current_chunk = merge_chunk_to_chunk(current_chunk, fixed_size_chunks[0])
                last_atomic = atomic["atomic_order"]

                flush_chunk()

                chunks.extend(fixed_size_chunks[1:])
                current_chunk = new_chunk(chunk_section_path, filename)
                continue

        current_chunk = merge_atomic_to_chunk(current_chunk, atomic)
        last_atomic = atomic["atomic_order"]

    # flush chunk cuối
    if current_chunk["metadata"]["token_count"] > 0:
        flush_chunk()

    return chunks
        

def create_chunk(node, cursor, file_path):
# hàm này tạo các chunk từ một node trên cây hierarchy
# trả về một mảng chunks

# xử lý cả trường hợp node này đủ cho token max rồi hoặc còn lớn hơn
    node_gold_units = get_all_gold_unit(node)
    atomics = load_atomic_content(cursor, node_gold_units)
    if node["token_count"] == 0:
        return []
    
    print("\nCREATE CHUNK")
    print(node)
    base_path = node["metadata"]["description"]
    
    chunks = []
    
    
    # case 1: nếu cả node < max token => node thành 1 chunk
    if node["token_count"] <= CHUNK_MAX_TOKEN:
        sum_token = node["token_count"]
        chunk = chunk_from_atomics(atomics=atomics, sum_token=sum_token, base_path=base_path, file_path=file_path)
        chunks.append(chunk)
        return chunks
    
    
    # case 2: nếu node lá vẫn lớn hơn max_token, thì split bởi subheadding nhận diện bên trong (nottoc)
    blocks = split_by_nottoc(atomics)
    for block in blocks:
        # tính token
        block_token = sum(row["token_count"] for row in block)
        
        # nếu token thỏa thì tạo 1 chunk từ toàn bộ atomics của block này (chunk = sub heading)
        nottoc = block[0]["content"].lstrip("#").strip()  # assume element đầu tiên là tiêu đề subheadding 
        if not base_path.endswith(nottoc):
            block_path = base_path + " > " + nottoc
        else:
            block_path = base_path
            
        if block_token <= CHUNK_MAX_TOKEN:
            chunk = chunk_from_atomics(block, file_path, block_token, block_path)
            chunks.append(chunk)
            continue
        
        # nếu không thì gọi hàm chunk nhỏ hơn
        c_chunks = chunk_by_semantic_units(atomics=block, file_path=file_path, chunk_section_path=block_path)
        chunks.extend(c_chunks)
    return chunks    
    
    
def build_chunks(node, file_path, cursor): 
# bắt đầu từ root node, chia dần xuống các level con cho tới khi thỏa max token
    
    if (node["token_count"]<=CHUNK_MAX_TOKEN):
        print("chunk is less than max token")
        if node is not None:
            print(node["title"])
        else:
            print("node is none")    
        chunks = create_chunk(node=node, cursor=cursor, file_path=file_path) # tạo luôn chunk từ node
        return chunks
    else:
        print("chunk is biggerr than max token")
        if node is not None:
            print(node["title"])
        else:
            print("node is none")  
            
        chunks = []
        if "children" in node and node["children"]:  
            for child in node["children"]:
                chunks.extend(build_chunks(child, file_path, cursor))  
            return chunks    
        
        # nếu đã là node lá mà còn lớn hơn max token
            # tạo các chunk từ node này
        node_chunks = create_chunk(node=node, file_path=file_path, cursor=cursor)
        chunks.extend(node_chunks)
        return chunks    
        
    