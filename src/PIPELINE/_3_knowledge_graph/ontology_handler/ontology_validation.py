# Cụ thể với batch này:

# Với các chunk should_extract=False:
# Không insert entity/relationship.
# Mark graph_processed=true.
# Có thể lưu thêm graph_skipped=true, graph_skip_reason.
# Với các chunk should_extract=True, validate trước:
# Normalize canonical name / aliases (casefold, trim, singular convention).
# Xóa alias trùng canonical.
# Kiểm tra relationship source và target đều có trong entity list của chính chunk đó.
# Dedupe relationship trùng hoàn toàn trong batch.
# Kiểm tra domain/range của relation type.
# Loại edge sai nghĩa nhưng không tự sửa.
from typing import Literal

from PIPELINE._3_knowledge_graph.ontology_handler.helpers import _normalize_text, _singularize_last_word
from PIPELINE._3_knowledge_graph.ontology_handler.ontology_definition import RELATION_TYPE_CONSTRAINTS
from PIPELINE._3_knowledge_graph.ontology_handler.ontology_extractor import ChunkExtractionResult, ExtractedEntity, ExtractedRelationship
from pydantic import BaseModel, Field

class RejectedGraphElement(BaseModel):
    element_kind: Literal["entity", "relationship"]
    element: dict
    reason: str

class ValidatedChunkResult(BaseModel):
    database_id: int
    chunk_id: str
    document_id: str

    is_skipped: bool = False
    skip_reason: str = ""

    valid_entities: list[ExtractedEntity] = Field(default_factory=list)
    valid_relationships: list[ExtractedRelationship] = Field(default_factory=list)
    rejected_elements: list[RejectedGraphElement] = Field(default_factory=list)

def normalize_entity(entity: ExtractedEntity) -> ExtractedEntity:
    """
    Return a cleaned copy of one extracted entity.

    - canonical_name: whitespace-normalized and converted to a conservative
      singular form.
    - aliases: whitespace-normalized, deduplicated case-insensitively.
    - aliases equal to canonical_name after trim/casefold are removed.
    - Singular/plural aliases are retained when they are not textually equal
      to the canonical name.
    """
    canonical_name = _singularize_last_word(
        _normalize_text(entity.canonical_name)
    )

    canonical_key = canonical_name.casefold()
    seen_alias_keys: set[str] = set()
    normalized_aliases: list[str] = []

    for alias in entity.aliases:
        normalized_alias = _normalize_text(alias)

        if not normalized_alias:
            continue

        alias_key = normalized_alias.casefold()

        # Removes only identical spelling/casing variants of canonical.
        # E.g. "Software Engineer" is removed, but
        # "Software Engineers" remains as a valid plural alias.
        if alias_key == canonical_key:
            continue

        if alias_key in seen_alias_keys:
            continue

        seen_alias_keys.add(alias_key)
        normalized_aliases.append(normalized_alias)

    return entity.model_copy(
        update={
            "canonical_name": canonical_name,
            "aliases": normalized_aliases,
            "description": _normalize_text(entity.description),
        }
    )


def _entity_key(name: str) -> str:
    return _normalize_text(name).casefold()


def validate_relationship_source_and_target(
    relationship: ExtractedRelationship,
    entity_by_name: dict[str, ExtractedEntity],
) -> tuple[bool, str]:
    """
    Validate that relationship endpoints refer to canonical entities
    in the normalized entity list for the current chunk.
    """
    source_key = _entity_key(relationship.source)
    target_key = _entity_key(relationship.target)

    missing_endpoints: list[str] = []

    if source_key not in entity_by_name:
        missing_endpoints.append(f"source '{relationship.source}'")

    if target_key not in entity_by_name:
        missing_endpoints.append(f"target '{relationship.target}'")

    if missing_endpoints:
        return (
            False,
            "Relationship endpoint is not a canonical entity in this chunk: "
            + ", ".join(missing_endpoints),
        )

    return True, ""


def validate_relation_domain_range(
    relationship: ExtractedRelationship,
    entity_by_name: dict[str, ExtractedEntity],
) -> tuple[bool, str]:
    constraint = RELATION_TYPE_CONSTRAINTS.get(relationship.relation_type)

    if constraint is None:
        return True, ""

    source = entity_by_name[_entity_key(relationship.source)]
    target = entity_by_name[_entity_key(relationship.target)]

    allowed_source_types = constraint.get("source_types")
    if allowed_source_types and source.type not in allowed_source_types:
        return (
            False,
            f"{relationship.relation_type} cannot have source type "
            f"{source.type}. Allowed: {sorted(allowed_source_types)}.",
        )

    allowed_target_types = constraint.get("target_types")
    if allowed_target_types and target.type not in allowed_target_types:
        return (
            False,
            f"{relationship.relation_type} cannot have target type "
            f"{target.type}. Allowed: {sorted(allowed_target_types)}.",
        )

    return True, ""


def validate_chunk_result(
    chunk_result: ChunkExtractionResult,
) -> ValidatedChunkResult:
    if not chunk_result.ontology.should_extract:
        return ValidatedChunkResult(
            database_id=chunk_result.database_id,
            chunk_id=chunk_result.chunk_id,
            document_id=chunk_result.document_id,
            is_skipped=True,
            skip_reason=chunk_result.ontology.skip_reason,
        )

    normalized_entities: list[ExtractedEntity] = []
    valid_relationships: list[ExtractedRelationship] = []
    rejected_elements: list[RejectedGraphElement] = []

    for entity in chunk_result.ontology.entities:
        normalized_entity = normalize_entity(entity) # to single, remove redundant aliases
        normalized_entities.append(normalized_entity)

    entity_by_name = {
        _entity_key(entity.canonical_name): entity
        for entity in normalized_entities
    }
    

    for relationship in chunk_result.ontology.relationships:
        is_valid_endpoints, endpoint_reason = (
            validate_relationship_source_and_target( # source and target are in the entities
                relationship=relationship,
                entity_by_name=entity_by_name,
            )
        )

        if not is_valid_endpoints:
            rejected_elements.append(
                RejectedGraphElement(
                    element_kind="relationship",
                    element=relationship.model_dump(),
                    reason=endpoint_reason,
                )
            )
            continue

        is_valid_domain_range, domain_range_reason = ( # source type A can only have relationship x with target type B
            validate_relation_domain_range(
                relationship=relationship,
                entity_by_name=entity_by_name,
            )
        )

        if not is_valid_domain_range:
            rejected_elements.append(
                RejectedGraphElement(
                    element_kind="relationship",
                    element=relationship.model_dump(),
                    reason=domain_range_reason,
                )
            )
            continue

        valid_relationships.append(relationship)

    return ValidatedChunkResult(
        database_id=chunk_result.database_id,
        chunk_id=chunk_result.chunk_id,
        document_id=chunk_result.document_id,
        is_skipped=False,
        skip_reason="",
        valid_entities=normalized_entities,
        valid_relationships=valid_relationships,
        rejected_elements=rejected_elements,
    )
        
    
    
def validate_ontologies(
    chunk_results: list[ChunkExtractionResult],
) -> list[ValidatedChunkResult]:
    validated: list[ValidatedChunkResult] = []

    for chunk_result in chunk_results:
        validated_chunk_result = validate_chunk_result(chunk_result)
        validated.append(validated_chunk_result)

    return validated
            
# For now, only merge relationships when their source, relation type, and target are all identical. Store the supporting evidence as a list:

# evidence = [
#     {
#         "database_id": 5859,
#         "description": "Software engineers use tools to improve software products.",
#     },
#     {
#         "database_id": 6001,
#         "description": "Software engineers use tools during development.",
#     },
# ]

# Handling semantically equivalent relationships expressed in the reverse direction will be deferred 
# until the graph data has been observed and evaluated. 

# todo
# → tách skipped results và non-skipped results

# non-skipped results
# → gom valid_entities của toàn batch
# → deduplicate entities trong batch
# → tạo mapping entity name cũ → entity canonical trong batch

# → gom valid_relationships của toàn batch
# → remap source/target theo entity mapping
# → deduplicate relationships bằng
#    (normalized_source, relation_type, normalized_target)
# → gộp evidence theo database_id + description

# → resolve entities với Neo4j graph hiện có
# → Neo4j MERGE nodes, edges, provenance/evidence

# → Neo4j write thành công
# → update PostgreSQL graph_processed=true

def dedup_entites_and_relationships(validated_ontologies: list[ValidatedChunkResult]):
    for ontology in validated_ontologies:
        if ontology.is_skipped:
            continue
        