# # Với mỗi EntityCandidate, tìm xem trong Neo4j có entity nào được xem là cùng thực thể với nó không.
# # Nếu có → merge/update thông tin của candidate vào node hiện tại.
# # Nếu không → tạo node mới.
# # Lưu mapping kiểu candidate/local_reference -> 
# # neo4j entity_id, vì relationship phía sau sẽ cần biết source/target cuối cùng là node nào.

# # relationship: lại dí vào entities
# # rồi mới kiểm tra (source_node)-[:USES]->(target_node) đã tồn tại chưa
# # Nếu chưa có → create relationship.

# # Nếu đã có → thường không tạo relationship duplicate, 
# # mà merge properties/evidences của occurrence mới vào relationship cũ.
# from PIPELINE._3_knowledge_graph.ontology_handler.ontology_validator_resolver import EntityCandidate, RelationshipCandidate

# def resolve_entites(entitie_candidates: list[EntityCandidate]):
# # EntityCandidate
# #       ↓
# # retrieve possible matches from Neo4j
# #       ↓
# # [5–20 candidates chẳng hạn]
# #       ↓
# # apply stricter resolution rules
# #       ↓
# # best match / no match

# Incoming EntityCandidate
#         ↓
# Lấy canonical_name + aliases
#         ↓
# Query Neo4j để tìm possible matches
#         ↓
# Không có candidate
#     → CREATE

# Có candidate
#         ↓
# Chấm từng candidate theo rule
#         ↓
# Có một match đủ chắc
#     → MERGE vào node đó

# Không match đủ chắc
#     → CREATE node mới

# def convert_elements_to_graph_properties(entities: list[EntityCandidate], relationships: list[RelationshipCandidate]):
    


# # LLM extraction
# #       ↓
# # validation
# #       ↓
# # dedup within current batch
# #       ↓
# # EntityCandidate / RelationshipCandidate
# #       ↓
# # resolve against persistent Neo4j graph   ← BẠN ĐANG Ở ĐÂY
# #       ↓
# # merge/create entities
# #       ↓
# # merge/create relationships
