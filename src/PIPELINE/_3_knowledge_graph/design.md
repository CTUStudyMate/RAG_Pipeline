(:Entity)-[:MENTIONED_IN]->(:Chunk)

(:Entity)-[:USES|IS_A|PART_OF|...]->(:Entity)

# ENTITY SHAPE
Entity
- entity_id
- canonical_name
- normalized_name
- aliases
- normalized_aliases
- observed_types

# CHUNK SHAPE
Chunk
- chunk_id
- document_id

# ENTITY vs Chunk
(Entity)-[:MENTIONED_IN_CHUNK {
    description
}]->(Chunk)

# RELATIONSHIP SHAPE
Relationship
- source_entity_id
- relation_type
- target_entity_id
- evidence_chunk_ids
- evidence_document_ids
- evidence_descriptions
