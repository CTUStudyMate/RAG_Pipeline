import copy
import base64
import json
import pandas as pd
import hashlib
from collections import deque
import tiktoken

from PIPELINE._3_chunk.common_utils import mannual_token_count
from PIPELINE._3_chunk.strategies.HSF.atomic_db_helpers.db_helpers import insert_atomic_into_db
from common_utils import filename_handle
import re
import math

import pipeline_config as conf

from src.PIPELINE._3_chunk.strategies.HSF.process_helpers.extract import extract_id_unit
from src.PIPELINE._3_chunk.strategies.HSF.process_helpers.normalize import is_heading_match, is_title_match, normalize_docname

# encoding = tiktoken.encoding_for_model("gpt-4o-mini")

def normalize_heading_display(text):
    if text.isupper():
        return text.title()
    return text


def resolve_cref(doc, cref):
    _, collection, idx = cref.split("/")
    collection_obj = getattr(doc, collection)   # lấy attribute động
    return collection_obj[int(idx)]


def make_id(text: str):
    normalized = " ".join(text.split())  # normalize whitespace
    return hashlib.md5(normalized.encode()).hexdigest()


def is_text_incomplete(text: str) -> bool:
    """
    Return True nếu text có dấu hiệu bị cắt giữa chừng.
    Return False nếu có vẻ đã kết thúc hoàn chỉnh.
    """
    if not text or not text.strip():
        return False

    text = text.strip()

    if not re.search(r'[.!?]"?$|[.!?]$|[”"\')\]]$', text):
        if text[-1].isalnum():
            return True

    dangling_words = {
        "and", "or", "but", "so", "because",
        "of", "in", "on", "at", "to", "for",
        "with", "by", "as", "that", "which"
    }

    last_word = text.split()[-1].lower()
    if last_word in dangling_words:
        return True

    if text.count("(") > text.count(")"):
        return True
    if text.count("[") > text.count("]"):
        return True
    if text.count("{") > text.count("}"):
        return True

    if text.count('"') % 2 != 0:
        return True
    if text.count("“") != text.count("”"):
        return True

    return False


def handle_batch_result(flat_list, my_built_dfs, batch_result, stream_elements, current_atomic_order, 
                        incomplete_atomic, doc_db_cursor, conn2, passed_cursor, open_node, node,
                        current_open_level, current_level_path_description):
    docname = normalize_docname(batch_result.name)
    
    cursor = passed_cursor
    
    # current_level_path = [0]
    
    if "metadata" not in open_node:
        open_node["metadata"] = {
            "description": ""
        }
    
    header_marks = ["section_header"]
    # region Looping through each parsed element
    for ref in flat_list:
        ori_element = ref.resolve(batch_result)
        ori_type = ori_element.label.value
        # print(ori_element.self_ref)
        
        # region The element is a heading
        if ori_type in header_marks:
            # print("FOUND TITLE:",ori_element.text)
            
            # case 1: the end of toc or it is a heading not present in toc
               # just simply append it to the current open node and mark it as a not-in-toc heading
            if not node or not is_title_match(ori_element, node):
                # print(f"Not match. Expected:  {node["title"]} - {node["page"]}, got {ori_element.text} - {ori_element.prov[0].page_no}")
                context_string = ori_element.text
                if "gold_unit" not in open_node:
                    open_node["gold_unit"] = []
                
                description_str = " > ".join(current_level_path_description).strip()
                
                gold_unit = {
                    "id": "",
                    "type": ori_element.label.value,
                    "content": f"### {context_string}" ,
                    "metadata": {
                        "description": description_str,
                        "heading": "nottoc",
                        "atomic_order": current_atomic_order
                    }
                }
                temp_id = make_id(ori_element.text)
                id_md5 = f"{docname}__nottoc_heading.{temp_id}.{current_atomic_order}"
                
                gold_unit["id"] = id_md5
                
                open_node["gold_unit"].append(id_md5)
                
                token_count = mannual_token_count(gold_unit["content"])
                # token_count = len(tokens)
                gold_unit["token_count"] = token_count
                stream_elements.append(gold_unit)
                current_atomic_order +=1
                continue
            
            # case 2: It is the title in the toc
            # print("\n----find match:")
            # print(ori_element.text),
            # print(node["title"])
            
            current_level = int(node["level"])
            store_title = normalize_heading_display(ori_element.text)
            
            if current_level > current_open_level:
                # current_level_path.append(1)
                
                current_level_path_description.append(store_title)
            elif current_level == current_open_level:
                # current_level_path[-1] += 1
                
                current_level_path_description[-1] = store_title
            else:
                # current_level_path = current_level_path[:current_level+1]
                # current_level_path[-1] += 1               
                
                current_level_path_description = current_level_path_description[:current_level]
                current_level_path_description[-1] = store_title

            current_open_level = current_level
            description_str = " > ".join(current_level_path_description).strip()
            
            if "gold_unit" not in node:
                node["gold_unit"] = []
            gold_unit = {
                "id": "",
                "type": ori_element.label.value,
                "content": store_title,
                "metadata": {
                    "description": description_str,
                    "level": current_level,
                    "atomic_order": current_atomic_order,
                    "heading": "main"
                }
            }
            id_md5 = make_id(ori_element.text)  
            heading_id = f"{docname}__heading.{id_md5}"
            gold_unit["id"] = heading_id
            
            # tokens = encoding.encode(gold_unit["content"])
            # token_count = len(tokens)
            token_count = mannual_token_count(gold_unit["content"])
            gold_unit["token_count"] = token_count
            
            stream_elements.append(gold_unit) ###
            current_atomic_order +=1
            
            # path_str = ".".join(map(str, current_level_path[1:]))
            node["metadata"] = {
                "docling_data":{
                    "text": store_title
                },
                # "path": path_str,
                "description": description_str
            }
            node["gold_unit"] = [heading_id]
            
            open_node = cursor.next()
            node = cursor.peek()
          
        
        # region The element is not a header    
        else:
            if "gold_unit" not in open_node:
                open_node["gold_unit"] = []
            gold_unit = {
                "id": "",
                "type": ori_element.label.value,
                "content": "",
                "metadata": {
                    "description": "",
                    "atomic_order": current_atomic_order
                }
            }  
            
            id_md5 = ""
            
            # special! picture can be a heading
            if ori_element.label.value == "picture":
                if (node is not None) and ori_element.prov[0].page_no == node["page"]:
                    # print("FIND SUSPICIOUS PICTURREEEE")
                    extracted_text = ""
                    for child in ori_element.children:
                        child_cref = child.cref
                        # text_extract_el = child_cref.resolve(batch_result.document)
                        text_extract_el = resolve_cref(batch_result, child_cref)
                        extracted_text += text_extract_el.text + " "
                        # print(extracted_text)
                    if is_heading_match(extracted_text, node["title"]):
                        # print("\n----Match !!!:")
                        
                        current_level = int(node["level"])
                        if current_level > current_open_level:
                            # current_level_path.append(1)
                            # current_level_path_description.append(node["title"])
                            current_level_path_description.append(extracted_text)
                        elif current_level == current_open_level:
                            # current_level_path[-1] += 1
                            # current_level_path_description[-1] = node["title"]
                            current_level_path_description[-1] = extracted_text
                        else:
                            # current_level_path = current_level_path[:current_level+1]
                            # current_level_path[-1] += 1
                            current_level_path_description = current_level_path_description[:current_level]
                            # current_level_path_description[-1] = node["title"]
                            current_level_path_description[-1] = extracted_text

                        current_open_level = current_level
                        description_str = " > ".join(current_level_path_description).strip()
                        
                        if "gold_unit" not in node:
                            node["gold_unit"] = []
                            
                        gold_unit = {
                            "id": "",
                            "type": ori_element.label.value,
                            "content": node["title"],
                            "metadata": {
                                "description": description_str,
                                "level": current_level,
                                "atomic_order": current_atomic_order,
                                "heading": "main"
                            }
                        }
                        id_md5 = make_id(node["title"])  
                        heading_id = f"{docname}__heading.{id_md5}"
                        gold_unit["id"] = heading_id
                        
                        # tokens = encoding.encode(gold_unit["content"])
                        # token_count = len(tokens)
                        token_count = mannual_token_count(gold_unit["content"])
                        gold_unit["token_count"] = token_count
                        
                        stream_elements.append(gold_unit) ###
                        current_atomic_order +=1
                        
                        # path_str = ".".join(map(str, current_level_path[1:]))
                        # print("PATH ARR")
                        # print(path_str)
                        node["metadata"] = {
                            "docling_data":{
                                "text": f"{extracted_text}"
                            },
                            # "path": path_str,
                            "description": description_str
                        }
                        node["gold_unit"] = [heading_id]
                        
                        open_node = cursor.next()
                        node = cursor.peek()
                        
                    else:
                        image = ori_element.image   
                        gold_unit["content"] = str(image.uri)
                        id_md5 = f"fig.{current_atomic_order}"
                        token_count = 300
                        gold_unit["token_count"] = token_count
                    
                else:
                    image = ori_element.image   
                    gold_unit["content"] = str(image.uri)
                    id_md5 = f"fig.{current_atomic_order}"
                    token_count = 300
                    gold_unit["token_count"] = token_count    
            
            elif ori_element.label.value in ["page_footer", "page_header"]:
                continue
            
            elif ori_element.label.value == "text":
                if incomplete_atomic:
                    stream_elements[-1]["content"] += ori_element.text
                else:
                    gold_unit["content"] =  ori_element.text
                    unit = extract_id_unit(ori_element)
                    temp_id = make_id(unit)
                    id_md5 = f"p.{temp_id}.{current_atomic_order}"
            
            elif ori_element.label.value == "table":
                table_df: pd.DataFrame = ori_element.export_to_dataframe(doc=batch_result)
                gold_unit["content"] = table_df.to_markdown()
                id_md5 = f"tbl.{current_atomic_order}"

            elif ori_element.label.value == "formula":
                formula_content = ori_element.orig.strip()
                if formula_content:
                    formatted = f"[FORMULA]\n{formula_content}"
                gold_unit["content"] =formatted if formatted else formula_content
                id_md5 = f"{ori_element.label.value}.{current_atomic_order}"
            
            elif ori_element.label.value in ["footnote"]:
                mark_content = ori_element.label.value
                if hasattr(ori_element, "text") and ori_element.text:
                    content = f"({mark_content}: {ori_element.text.strip()})"
                else:
                    content = ""
                id_md5 = f"{ori_element.label.value}.{current_atomic_order}"
                gold_unit["content"] = content
                
            elif ori_element.label.value == "list_item":
                gold_unit["content"] =  f" - {ori_element.text}"
                id_md5 = f"{ori_element.label.value}.{current_atomic_order}"
                
            elif ori_element.label.value == "caption":
                # print("\n\nCAPPTIONNN")
                # print(ori_element)
                gold_unit["content"] =  f"[{ori_element.text}] "
                id_md5 = f"{ori_element.label.value}.{current_atomic_order}"    
                
            else:
                content = ""
                id_md5 = f"unknown_type.{current_atomic_order}"
                gold_unit["content"] = content
            
            
            # description_str = " > ".join(current_level_path_description)
            # gold_unit["metadata"]["description"] = description_str
            
            if ori_element.label.value != "picture":
                # tokens = encoding.encode(gold_unit["content"])
                # token_count = len(tokens) 
                token_count = mannual_token_count(gold_unit["content"]) 
                gold_unit["token_count"] = token_count
            
            el_id = f"{docname}__{id_md5}"
            gold_unit["id"] = el_id
            open_node["gold_unit"].append(el_id)
            stream_elements.append(gold_unit)
            current_atomic_order +=1
            
            incomplete_atomic = False
    
        if len(stream_elements) > conf.WRITE_FILE_AFTER_N_STREAM_ELEMENTS:
            element = stream_elements.popleft()
            element["metadata"]["source_document"] = batch_result.name
            #======= TEST STREAM ELEMENT =========
            # target_file = conf.STREAM_ELEMENTS_FILEPATH
            # with open(target_file, "a", encoding="utf-8") as f:
            #     json.dump(element, f, default=str, ensure_ascii=False, indent=4)
            #     f.write("\n")
            #=====================================    
            
            insert_atomic_into_db(cursor=doc_db_cursor, element=element)
            conn2.commit()
            
    last_element = stream_elements[-1]
    if (last_element["type"] == "text"):
        if is_text_incomplete(last_element["content"]):  # ===== FIX =====
            incomplete_atomic = True


    #======= TEST TREE  ==================
    tree_file = f"{docname}_test_tree.json"
    with open(tree_file, "w", encoding="utf-8") as f:
        json.dump(my_built_dfs, f, ensure_ascii=False, indent=4)          
    #=====================================    
          
    return current_atomic_order, incomplete_atomic, cursor, open_node, node, current_open_level, current_level_path_description