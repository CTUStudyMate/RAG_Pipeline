# RELATIONSHIPS
# RelationshipCandidate[]
#         ↓
# map local entity id → graph entity id
#         ↓
# dedup nội bộ batch theo
# (source_graph_id, relation_type, target_graph_id)
#         ↓
# query Neo4j 1 lần / 1 batch lớn
# để lấy các relationship đã tồn tại
#         ↓
# so sánh trong Python
#         ↓
# chỉ CREATE những cái chưa có
# và merge evidence cho những cái đã có
from PIPELINE._3_knowledge_graph.ontology_handler.ontology_definition import RELATION_TYPES
from PIPELINE._3_knowledge_graph.ontology_handler.ontology_validator_resolver import RelationshipCandidate
from pydantic import BaseModel, Field
from neo4j import Driver

class GraphRelationship(BaseModel):
    source_entity_id: str
    relation_type: RELATION_TYPES
    target_entity_id: str

    evidence_chunk_ids: list[str] = Field(default_factory=list)
    evidence_document_ids: list[str] = Field(default_factory=list)
    evidence_descriptions: list[str] = Field(default_factory=list)
    
    
def remap_relationships(
    relationships: list[RelationshipCandidate],
    entity_id_map: dict[str, str],
) -> list[RelationshipCandidate]:

    remapped_relationships: list[RelationshipCandidate] = []

    for relationship in relationships:
        remapped_relationships.append(
            RelationshipCandidate(
                source_entity_id=entity_id_map[
                    relationship.source_entity_id
                ],
                target_entity_id=entity_id_map[
                    relationship.target_entity_id
                ],
                relation_type=relationship.relation_type,
                chunk_evidences=relationship.chunk_evidences,
            )
        )

    return remapped_relationships

def dedup_remapped_relationships(
    relationships: list[RelationshipCandidate],
) -> list[RelationshipCandidate]:

    relationship_map: dict[
        tuple[str, RELATION_TYPES, str],
        RelationshipCandidate
    ] = {}

    for relationship in relationships:
        key = (
            relationship.source_entity_id,
            relationship.relation_type,
            relationship.target_entity_id,
        )

        if key not in relationship_map:
            relationship_map[key] = RelationshipCandidate(
                source_entity_id=relationship.source_entity_id,
                target_entity_id=relationship.target_entity_id,
                relation_type=relationship.relation_type,
                chunk_evidences=list(relationship.chunk_evidences),
            )
            continue

        existing_relationship = relationship_map[key]

        existing_chunk_ids = {
            evidence.chunk_id
            for evidence in existing_relationship.chunk_evidences
        }

        for evidence in relationship.chunk_evidences:
            if evidence.chunk_id not in existing_chunk_ids:
                existing_relationship.chunk_evidences.append(evidence)
                existing_chunk_ids.add(evidence.chunk_id)

    return list(relationship_map.values())

def retrieve_existing_relationships(
    relationships: list[RelationshipCandidate],
    driver: Driver,
    database: str,
) -> dict[tuple[str, str, str], GraphRelationship]:

    relationship_keys = [
        {
            "source_entity_id": relationship.source_entity_id,
            "relation_type": (
                relationship.relation_type.value
                if hasattr(relationship.relation_type, "value")
                else relationship.relation_type
            ),
            "target_entity_id": relationship.target_entity_id,
        }
        for relationship in relationships
    ]

    query = """
    UNWIND $relationship_keys AS rel

    MATCH (source:Entity {entity_id: rel.source_entity_id})
          -[r]->
          (target:Entity {entity_id: rel.target_entity_id})

    WHERE type(r) = rel.relation_type

    RETURN
        source.entity_id AS source_entity_id,
        type(r) AS relation_type,
        target.entity_id AS target_entity_id,
        r.evidence_chunk_ids AS evidence_chunk_ids,
        r.evidence_document_ids AS evidence_document_ids,
        r.evidence_descriptions AS evidence_descriptions
    """

    records, _, _ = driver.execute_query(
        query,
        relationship_keys=relationship_keys,
        database_=database,
    )

    existing_relationships: dict[
        tuple[str, str, str],
        GraphRelationship
    ] = {}

    for record in records:
        key = (
            record["source_entity_id"],
            record["relation_type"],
            record["target_entity_id"],
        )

        existing_relationships[key] = GraphRelationship(
            source_entity_id=record["source_entity_id"],
            relation_type=record["relation_type"],
            target_entity_id=record["target_entity_id"],
            evidence_chunk_ids=record["evidence_chunk_ids"] or [],
            evidence_document_ids=record["evidence_document_ids"] or [],
            evidence_descriptions=record["evidence_descriptions"] or [],
        )

    return existing_relationships

def create_relationship(
    relationship: RelationshipCandidate,
    driver: Driver,
    database: str,
):
    relation_type = (
        relationship.relation_type.value
        if hasattr(relationship.relation_type, "value")
        else relationship.relation_type
    )

    evidence_chunk_ids = [
        evidence.chunk_id
        for evidence in relationship.chunk_evidences
    ]

    evidence_document_ids = [
        evidence.document_id
        for evidence in relationship.chunk_evidences
    ]

    evidence_descriptions = [
        evidence.description
        for evidence in relationship.chunk_evidences
    ]

    query = f"""
    MATCH (source:Entity {{entity_id: $source_entity_id}})
    MATCH (target:Entity {{entity_id: $target_entity_id}})

    CREATE (source)-[r:{relation_type} {{
        evidence_chunk_ids: $evidence_chunk_ids,
        evidence_document_ids: $evidence_document_ids,
        evidence_descriptions: $evidence_descriptions
    }}]->(target)

    RETURN r
    """

    driver.execute_query(
        query,
        source_entity_id=relationship.source_entity_id,
        target_entity_id=relationship.target_entity_id,
        evidence_chunk_ids=evidence_chunk_ids,
        evidence_document_ids=evidence_document_ids,
        evidence_descriptions=evidence_descriptions,
        database_=database,
    )
    
def merge_relationship(
    incoming_relationship: RelationshipCandidate,
    graph_relationship: GraphRelationship,
    driver: Driver,
    database: str,
):
    relation_type = (
        incoming_relationship.relation_type.value
        if hasattr(incoming_relationship.relation_type, "value")
        else incoming_relationship.relation_type
    )

    # Evidence hiện có trên graph
    evidence_by_chunk_id = {
        chunk_id: {
            "chunk_id": chunk_id,
            "document_id": document_id,
            "description": description,
        }
        for chunk_id, document_id, description in zip(
            graph_relationship.evidence_chunk_ids,
            graph_relationship.evidence_document_ids,
            graph_relationship.evidence_descriptions,
        )
    }

    # Add evidence mới nếu chunk_id chưa có
    for evidence in incoming_relationship.chunk_evidences:
        if evidence.chunk_id not in evidence_by_chunk_id:
            evidence_by_chunk_id[evidence.chunk_id] = {
                "chunk_id": evidence.chunk_id,
                "document_id": evidence.document_id,
                "description": evidence.description,
            }

    merged_evidences = list(evidence_by_chunk_id.values())

    evidence_chunk_ids = [
        evidence["chunk_id"]
        for evidence in merged_evidences
    ]

    evidence_document_ids = [
        evidence["document_id"]
        for evidence in merged_evidences
    ]

    evidence_descriptions = [
        evidence["description"]
        for evidence in merged_evidences
    ]

    query = f"""
    MATCH (source:Entity {{entity_id: $source_entity_id}})
          -[r:{relation_type}]->
          (target:Entity {{entity_id: $target_entity_id}})

    SET
        r.evidence_chunk_ids = $evidence_chunk_ids,
        r.evidence_document_ids = $evidence_document_ids,
        r.evidence_descriptions = $evidence_descriptions

    RETURN r
    """

    driver.execute_query(
        query,
        source_entity_id=incoming_relationship.source_entity_id,
        target_entity_id=incoming_relationship.target_entity_id,
        evidence_chunk_ids=evidence_chunk_ids,
        evidence_document_ids=evidence_document_ids,
        evidence_descriptions=evidence_descriptions,
        database_=database,
    )

def resolve_and_upsert_relationships(
    entity_map,
    relationship_candidates,
    driver,
    database: str,
):
    mapped_relationships = remap_relationships(
        relationships=relationship_candidates,
        entity_id_map=entity_map,
    )

    relationships_for_graph_process = dedup_remapped_relationships(
        relationships=mapped_relationships
    )

    graph_existing_relationships = retrieve_existing_relationships(
        relationships=relationships_for_graph_process,
        driver=driver,
        database=database,
    )

    for relationship in relationships_for_graph_process:
        relation_type = (
            relationship.relation_type.value
            if hasattr(relationship.relation_type, "value")
            else relationship.relation_type
        )

        key = (
            relationship.source_entity_id,
            relation_type,
            relationship.target_entity_id,
        )

        if key in graph_existing_relationships:
            merge_relationship(
                incoming_relationship=relationship,
                graph_relationship=graph_existing_relationships[key],
                driver=driver,
                database=database,
            )
        else:
            create_relationship(
                relationship=relationship,
                driver=driver,
                database=database,
            )
    
    
    
    