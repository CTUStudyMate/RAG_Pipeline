import copy
import json
from PIPELINE._3_chunk.strategies.HSF.atomic_db_helpers.db_helpers import connect_db, create_db_for_document
from PIPELINE._3_chunk.strategies.HSF.hierarchy_helpers.DFSCursor import DFSCursor


def sum_node_gold_units(node, token_map):

    gold_units = node.get("gold_unit", [])

    token_sum = 0
    for gid in gold_units:
        token_sum += token_map.get(gid) or 0

    return token_sum


def compute_node_token(node, token_map):

    token = sum_node_gold_units(node, token_map)

    for child in node.get("children", []):
        token += compute_node_token(child, token_map)

    node["token_count"] = token
    return token
    
    
def compute_tree_token(hierarchy_tree, cursor):
           
    cursor.execute("""
                    SELECT id, token_count FROM atomic_elements
                    """)

    token_map = dict(cursor.fetchall())
    all_token = compute_node_token(hierarchy_tree, token_map)
    
    # ======== TEST TOKEN TREE =======================
    with open("new_test_token_tree.json", "w", encoding="utf-8") as f:
        json.dump(hierarchy_tree, f, ensure_ascii=False, default=str, indent=2)
    # ===============================================    
   
    

# with open("se_theory_practice_test_tree.json", "r", encoding="utf-8") as f:
#     hierarchy_tree = json.load(f)
#     # print(hierarchy_tree)
    
# db_path = "data/db/se_theory_practice_20260314_194045.db"  
# conn = connect_db(db_path) 
# cursor = conn.cursor()

# cursor.execute("""
#                 SELECT id, token_count FROM atomic_elements
#                 """)

# token_map = dict(cursor.fetchall())

# hierarchy_tree2 = copy.deepcopy(hierarchy_tree)

# all_token = compute_node_token(hierarchy_tree2, token_map)

# with open("test_token_tree.json", "w", encoding="utf-8") as f:
#     json.dump(hierarchy_tree2, f, ensure_ascii=False, default=str, indent=2)

# print("tree token:", all_token)



# TEST COMPUTED TOKEN RESULT
# cursor.execute("""
# SELECT COALESCE(SUM(token_count),0) FROM atomic_elements
# """)

# real_token = cursor.fetchone()[0]

# print("db token:", real_token)
# print("match:", all_token == real_token)