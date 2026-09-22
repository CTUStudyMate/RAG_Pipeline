from PIPELINE._3_knowledge_graph.ontology_handler.helpers import check_one_way_name_values, check_reciprocal_name_values, normalize_name
from PIPELINE._3_knowledge_graph.ontology_handler.ontology_definition import ENTITY_TYPES
from PIPELINE._3_knowledge_graph.ontology_handler.ontology_validator_resolver import ChunkEvidence, EntityCandidate, RelationshipCandidate

from neo4j import Driver
from pydantic import BaseModel, Field


# ENTITIES
class GraphEntity(BaseModel):
    entity_id: str
    canonical_name: str
    normalized_name: str

    aliases: list[str] = Field(default_factory=list)
    normalized_aliases: list[str] = Field(default_factory=list)

    observed_types: list[ENTITY_TYPES] = Field(default_factory=list)

    chunk_evidences: list[ChunkEvidence] = Field(default_factory=list)
    
def retrieve_candidates( 
    entity: EntityCandidate,
    driver: Driver,
    database: str,
) -> list[GraphEntity]:
# hiện tại chỉ mới một cuốn sách nên kéo hết relevant entities về, sau phải kéo về theo batch
# khi kéo về theo batch thì phải so hết trong toàn bộ batches mới quyết định merge hay add
    names = [
        entity.canonical_name,
        *entity.aliases,
    ]

    normalized_names = {
        normalize_name(name)
        for name in names
    }

    query = """
    MATCH (e:Entity)
    WHERE e.normalized_name IN $incoming_names
    OR any(
        alias IN e.normalized_aliases
        WHERE alias IN $incoming_names
    )

    OPTIONAL MATCH (e)-[ev:MENTIONED_IN_CHUNK]->(c:Chunk)

    RETURN
        e,
        collect(
            CASE
                WHEN c IS NULL THEN null
                ELSE {
                    chunk_id: c.chunk_id,
                    document_id: c.document_id,
                    description: ev.description
                }
            END
        ) AS chunk_evidences
    """

    records, _, _ = driver.execute_query(
        query,
        incoming_names=list(normalized_names),
        database_=database,
    )

    candidates: list[GraphEntity] = []

    for record in records:
        entity_data = dict(record["e"])

        chunk_evidences = [
            ChunkEvidence.model_validate(evidence)
            for evidence in record["chunk_evidences"]
            if evidence is not None
        ]

        candidates.append(
            GraphEntity(
                **entity_data,
                chunk_evidences=chunk_evidences,
            )
        )

    return candidates

def create_entity(
    entity: EntityCandidate,
    driver: Driver,
    database: str,
):
    normalized_name = normalize_name(entity.canonical_name)

    normalized_aliases = list(
        dict.fromkeys(
            normalize_name(alias)
            for alias in entity.aliases
        )
    )

    observed_types = list(
        dict.fromkeys(
            entity_type.value
            if hasattr(entity_type, "value")
            else entity_type
            for entity_type in entity.observed_types
        )
    )

    query = """
    CREATE (e:Entity {
        entity_id: $entity_id,
        canonical_name: $canonical_name,
        normalized_name: $normalized_name,
        aliases: $aliases,
        normalized_aliases: $normalized_aliases,
        observed_types: $observed_types
    })

    RETURN e
    """

    driver.execute_query(
        query,
        entity_id=entity.entity_id,
        canonical_name=entity.canonical_name,
        normalized_name=normalized_name,
        aliases=entity.aliases,
        normalized_aliases=normalized_aliases,
        observed_types=observed_types,
        database_=database,
    )

    # Tạo / nối các Chunk evidence
    for evidence in entity.chunk_evidences:
        query = """
        MATCH (e:Entity {entity_id: $entity_id})

        MERGE (c:Chunk {chunk_id: $chunk_id})
        SET c.document_id = $document_id

        MERGE (e)-[r:MENTIONED_IN_CHUNK]->(c)
        SET r.description = $description
        """

        driver.execute_query(
            query,
            entity_id=entity.entity_id,
            chunk_id=evidence.chunk_id,
            document_id=evidence.document_id,
            description=evidence.description,
            database_=database,
        )

    return entity.entity_id
    
def merge_entity(
    incoming_entity: EntityCandidate,
    graph_entity: GraphEntity,
    driver: Driver,
    database: str,
):
    # 1. Merge aliases
    incoming_aliases = list(incoming_entity.aliases)

    # Nếu canonical name incoming khác canonical name hiện tại trong graph,
    # giữ canonical của graph và đưa canonical incoming thành alias.
    if (
        normalize_name(incoming_entity.canonical_name)
        != graph_entity.normalized_name
    ):
        incoming_aliases.append(incoming_entity.canonical_name)

    merged_aliases = list(
        dict.fromkeys([
            *graph_entity.aliases,
            *incoming_aliases,
        ])
    )

    # Không để canonical name hiện tại xuất hiện lại trong aliases
    merged_aliases = [
        alias
        for alias in merged_aliases
        if normalize_name(alias) != graph_entity.normalized_name
    ]

    normalized_aliases = list(
        dict.fromkeys(
            normalize_name(alias)
            for alias in merged_aliases
        )
    )

    # 2. Merge observed types
    merged_types = list(
        dict.fromkeys([
            *graph_entity.observed_types,
            *incoming_entity.observed_types,
        ])
    )

    # 3. Update Entity node
    query = """
    MATCH (e:Entity {entity_id: $entity_id})
    SET
        e.aliases = $aliases,
        e.normalized_aliases = $normalized_aliases,
        e.observed_types = $observed_types
    RETURN e
    """

    driver.execute_query(
        query,
        entity_id=graph_entity.entity_id,
        aliases=merged_aliases,
        normalized_aliases=normalized_aliases,
        observed_types=[
            entity_type.value
            if hasattr(entity_type, "value")
            else entity_type
            for entity_type in merged_types
        ],
        database_=database,
    )

    # 4. Chỉ merge các chunk evidence mới từ incoming entity
    for evidence in incoming_entity.chunk_evidences:
        query = """
        MATCH (e:Entity {entity_id: $entity_id})

        MERGE (c:Chunk {chunk_id: $chunk_id})
        SET c.document_id = $document_id

        MERGE (e)-[r:MENTIONED_IN_CHUNK]->(c)
        SET r.description = $description
        """

        driver.execute_query(
            query,
            entity_id=graph_entity.entity_id,
            chunk_id=evidence.chunk_id,
            document_id=evidence.document_id,
            description=evidence.description,
            database_=database,
        )

    return graph_entity.entity_id


def should_merge_by_context(entity, graph_entity):
    return True

def merge_or_create_entity(
    entity: EntityCandidate,
    relevant_entities: list[GraphEntity],
    driver: Driver,
    database: str,
) -> str:

    for graph_entity in relevant_entities:
        reciprocal_match = check_reciprocal_name_values(
            canonical_a=entity.canonical_name,
            aliases_a=entity.aliases,
            canonical_b=graph_entity.canonical_name,
            aliases_b=graph_entity.aliases,
        )

        same_canonical = (
            normalize_name(entity.canonical_name)
            == graph_entity.normalized_name
        )

        same_type = any(
            entity_type in graph_entity.observed_types
            for entity_type in entity.observed_types
        )

        one_way_match = check_one_way_name_values(
            canonical_a=entity.canonical_name,
            aliases_a=entity.aliases,
            canonical_b=graph_entity.canonical_name,
            aliases_b=graph_entity.aliases,
        )

        if reciprocal_match:
            return merge_entity(
                incoming_entity=entity,
                graph_entity=graph_entity,
                driver=driver,
                database=database,
            )

        if same_canonical and same_type:
            if should_merge_by_context(entity, graph_entity):
                return merge_entity(
                    incoming_entity=entity,
                    graph_entity=graph_entity,
                    driver=driver,
                    database=database,
                )

        # if same_type and one_way_match:
        #     if should_merge_by_context(entity, graph_entity):
        #         return merge_entity(
        #             incoming_entity=entity,
        #             graph_entity=graph_entity,
        #             driver=driver,
        #             database=database,
        #         )

    # Không match với entity nào trong graph
    return create_entity(
        entity=entity,
        driver=driver,
        database=database,
    )
    
def resolve_and_upsert_entites(
    entity_candidates: list[EntityCandidate],
    driver: Driver,
    database: str,
) -> dict[str, str]:

    graph_and_local_entities_map: dict[str, str] = {}

    for entity in entity_candidates:
        relevant_entities = retrieve_candidates(
            entity=entity,
            driver=driver,
            database=database,
        )

        graph_entity_id = merge_or_create_entity(
            entity=entity,
            relevant_entities=relevant_entities,
            driver=driver,
            database=database,
        )

        graph_and_local_entities_map[entity.entity_id] = graph_entity_id

    return graph_and_local_entities_map


    