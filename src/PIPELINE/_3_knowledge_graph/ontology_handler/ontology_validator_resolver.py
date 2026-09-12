"""
This file prepares the entities and relationships extracted from a batch of
chunks before they are merged into the graph.

After receiving extraction results for each chunk—including LLM-generated
entities and relationships together with the corresponding source-chunk
information—the pipeline performs several processing steps. The final output
is a list of entities and relationships in a standardized format, with
duplicates removed within each batch of chunks.

The main processing steps are:

* Clean and normalize each entity by converting canonical names to singular
  form, removing duplicate aliases, and trimming unnecessary whitespace in
  descriptions.

* Validate each relationship. A relationship is valid only when:

  * its source and target both exist in the entity list extracted from the
    same chunk; and
  * the source and target entity types satisfy the domain and range constraints
    of the relationship type.

* At this point, the pipeline has an initially processed list of entities and
  relationships.

* Deduplicate entities and relationships to remove repeated elements within
  the batch.

* The resulting entity and relationship lists are then ready for the
  subsequent graph-merging step.
"""

from typing import Literal
from uuid import uuid4

from PIPELINE._3_knowledge_graph.ontology_handler.helpers import _normalize_text, _singularize_last_word, is_fuzzy_match, normalize_text
from PIPELINE._3_knowledge_graph.ontology_handler.ontology_definition import ENTITY_TYPES, RELATION_TYPE_CONSTRAINTS, RELATION_TYPES
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

def _local_id_key(local_id: str) -> str:
    return local_id.strip().casefold()


def validate_relationship_source_and_target(
    relationship: ExtractedRelationship,
    entity_by_local_id: dict[str, ExtractedEntity],
) -> tuple[bool, str]:
    """
    Validate that relationship endpoints refer to entity local IDs
    extracted from the same chunk.
    """
    source_id_key = _local_id_key(
        relationship.source_entity_id
    )
    target_id_key = _local_id_key(
        relationship.target_entity_id
    )

    missing_endpoints: list[str] = []

    if source_id_key not in entity_by_local_id:
        missing_endpoints.append(
            f"source_entity_id '{relationship.source_entity_id}'"
        )

    if target_id_key not in entity_by_local_id:
        missing_endpoints.append(
            f"target_entity_id '{relationship.target_entity_id}'"
        )

    if missing_endpoints:
        return (
            False,
            "Relationship endpoint does not refer to an entity local_id "
            "in this chunk: "
            + ", ".join(missing_endpoints),
        )

    return True, ""


def validate_relation_domain_range(
    relationship: ExtractedRelationship,
    entity_by_local_id: dict[str, ExtractedEntity],
) -> tuple[bool, str]:
    constraint = RELATION_TYPE_CONSTRAINTS.get(
        relationship.relation_type
    )

    if constraint is None:
        return True, ""

    source = entity_by_local_id[
        _local_id_key(relationship.source_entity_id)
    ]
    target = entity_by_local_id[
        _local_id_key(relationship.target_entity_id)
    ]

    allowed_source_types = constraint.get("source_types")

    if (
        allowed_source_types
        and source.type not in allowed_source_types
    ):
        return (
            False,
            f"{relationship.relation_type} cannot have source type "
            f"{source.type}. Allowed: {sorted(allowed_source_types)}.",
        )

    allowed_target_types = constraint.get("target_types")

    if (
        allowed_target_types
        and target.type not in allowed_target_types
    ):
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
        normalized_entity = normalize_entity(entity)
        normalized_entities.append(normalized_entity)

    entity_by_local_id: dict[str, ExtractedEntity] = {}

    for entity in normalized_entities:
        local_id_key = _local_id_key(entity.local_id)

        if local_id_key in entity_by_local_id:
            raise ValueError(
                f"Duplicate entity local_id '{entity.local_id}' "
                f"in chunk {chunk_result.database_id}."
            )

        entity_by_local_id[local_id_key] = entity

    for relationship in chunk_result.ontology.relationships:
        is_valid_endpoints, endpoint_reason = (
            validate_relationship_source_and_target(
                relationship=relationship,
                entity_by_local_id=entity_by_local_id,
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

        is_valid_domain_range, domain_range_reason = (
            validate_relation_domain_range(
                relationship=relationship,
                entity_by_local_id=entity_by_local_id,
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
    
class ChunkValidationFailure(BaseModel):
    database_id: int
    chunk_id: str
    document_id: str
    error: str
      
def validate_ontologies(
    chunk_results: list[ChunkExtractionResult],
) -> tuple[
    list[ValidatedChunkResult],
    list[ChunkValidationFailure],
]:
    validated: list[ValidatedChunkResult] = []
    failures: list[ChunkValidationFailure] = []

    for chunk_result in chunk_results:
        try:
            validated_chunk_result = validate_chunk_result(
                chunk_result
            )
            validated.append(validated_chunk_result)

        except Exception as error:
            failures.append(
                ChunkValidationFailure(
                    database_id=chunk_result.database_id,
                    chunk_id=chunk_result.chunk_id,
                    document_id=chunk_result.document_id,
                    error=str(error),
                )
            )

    return validated, failures
            
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
class ChunkEvidence(BaseModel):
    database_id: int
    chunk_id: str
    document_id: str
    description: str


# final shape of entity and relationship
class EntityCandidate(BaseModel):
    entity_id: str
    canonical_name: str

    aliases: list[str] = Field(default_factory=list)

    # Có thể nhiều type sau reciprocal alias merge.
    observed_types: list[ENTITY_TYPES] = Field(default_factory=list)

    chunk_evidences: list[ChunkEvidence] = Field(default_factory=list)


# raw data
class EntityOccurrence(BaseModel):
    entity: ExtractedEntity
    evidence: ChunkEvidence


class RelationshipOccurrence(BaseModel):
    relationship: ExtractedRelationship
    evidence: ChunkEvidence
    
class RelationshipCandidate(BaseModel):
    source_entity_id: str
    target_entity_id: str

    relation_type: RELATION_TYPES

    chunk_evidences: list[ChunkEvidence] = Field(default_factory=list)

def check_reciprocal_names(
    current_entity: EntityOccurrence,
    source_entity: EntityCandidate,
) -> bool:
    """
    Check whether:
    - current entity's canonical name is an alias of the existing candidate;
    - existing candidate's canonical name is an alias of the current entity.
    """
    current_canonical = normalize_text(
        current_entity.entity.canonical_name
    )
    candidate_canonical = normalize_text(
        source_entity.canonical_name
    )

    current_aliases = {
        normalize_text(alias)
        for alias in current_entity.entity.aliases
    }
    candidate_aliases = {
        normalize_text(alias)
        for alias in source_entity.aliases
    }

    return (
        current_canonical in candidate_aliases
        and candidate_canonical in current_aliases
    )

def _dedupe_aliases(
    aliases: list[str],
    canonical_name: str,
) -> list[str]:
    canonical_key = normalize_text(canonical_name)
    seen_keys: set[str] = set()
    result: list[str] = []

    for alias in aliases:
        normalized_alias = normalize_text(alias)

        if not normalized_alias or normalized_alias == canonical_key:
            continue

        if normalized_alias in seen_keys:
            continue

        seen_keys.add(normalized_alias)
        result.append(alias.strip())

    return result

def _dedup_chunk_evidences(
    chunk_evidences: list[ChunkEvidence],
) -> list[ChunkEvidence]:
    seen_chunk_keys: set[tuple[int, str, str]] = set()
    merged_evidences: list[ChunkEvidence] = []

    for evidence in chunk_evidences:
        chunk_key = (
            evidence.database_id,
            evidence.chunk_id,
            evidence.document_id,
        )

        if chunk_key in seen_chunk_keys:
            continue

        seen_chunk_keys.add(chunk_key)
        merged_evidences.append(evidence)

    return merged_evidences

def merge_entity_candidate(
    candidate: EntityCandidate,
    occurrence: EntityOccurrence,
) -> EntityCandidate:
    entity = occurrence.entity

    # Nếu canonical khác candidate canonical, giữ nó như một alias.
    aliases_to_merge = [
        *candidate.aliases,
        *entity.aliases,
        entity.canonical_name,
    ]

    observed_types = list(candidate.observed_types)
    if entity.type not in observed_types:
        observed_types.append(entity.type)

    return candidate.model_copy(
        update={
            "aliases": _dedupe_aliases(
                aliases=aliases_to_merge,
                canonical_name=candidate.canonical_name,
            ),
            "observed_types": observed_types,
            "chunk_evidences": _dedup_chunk_evidences(
                [
                    *candidate.chunk_evidences,
                    occurrence.evidence,
                ]
            ),
        }
    )
    
def create_entity_candidate(
    occurrence: EntityOccurrence,
) -> EntityCandidate:
    entity = occurrence.entity

    return EntityCandidate(
        entity_id=str(uuid4()),
        canonical_name=entity.canonical_name,
        aliases=_dedupe_aliases(
            aliases=entity.aliases,
            canonical_name=entity.canonical_name,
        ),
        observed_types=[entity.type],
        chunk_evidences=[occurrence.evidence],
    )
 
def dedup_entities(
    entity_occurrences: list[EntityOccurrence],
) -> tuple[
    list[EntityCandidate],
    dict[tuple[str, str], str],
]:
    """
    Deduplicate entity occurrences within one batch.

    Returns:
        - deduplicated entity candidates;
        - mapping from (chunk_id, local_id) to candidate entity_id.
    """

    candidates: list[EntityCandidate] = []

    entity_id_by_local_reference: dict[
        tuple[str, str],
        str,
    ] = {}

    for occurrence in entity_occurrences:
        entity = occurrence.entity

        local_reference = (
            occurrence.evidence.chunk_id,
            _local_id_key(entity.local_id),
        )

        was_merged = False

        for index, candidate in enumerate(candidates):
            same_type = entity.type in candidate.observed_types

            canonical_names_match = is_fuzzy_match(
                entity.canonical_name,
                candidate.canonical_name,
            )

            reciprocal_names_match = check_reciprocal_names(
                current_entity=occurrence,
                source_entity=candidate,
            )

            if same_type and canonical_names_match:
                merged_candidate = merge_entity_candidate(
                    candidate=candidate,
                    occurrence=occurrence,
                )

                candidates[index] = merged_candidate

                entity_id_by_local_reference[local_reference] = (
                    merged_candidate.entity_id
                )

                was_merged = True
                break

            if reciprocal_names_match:
                merged_candidate = merge_entity_candidate(
                    candidate=candidate,
                    occurrence=occurrence,
                )

                candidates[index] = merged_candidate

                entity_id_by_local_reference[local_reference] = (
                    merged_candidate.entity_id
                )

                was_merged = True
                break

        if not was_merged:
            new_candidate = create_entity_candidate(occurrence)
            candidates.append(new_candidate)

            entity_id_by_local_reference[local_reference] = (
                new_candidate.entity_id
            )

    return candidates, entity_id_by_local_reference

def merge_relationship(
    current_relationship: RelationshipOccurrence,
    target: RelationshipCandidate,
) -> RelationshipCandidate:
    merged_evidences = _dedup_chunk_evidences(
        [
            *target.chunk_evidences,
            current_relationship.evidence,
        ]
    )

    return target.model_copy(
        update={
            "chunk_evidences": merged_evidences,
        }
    )  

def dedup_relationships(
    relationships: list[RelationshipOccurrence],
    entity_id_by_local_reference: dict[tuple[str, str], str],
) -> list[RelationshipCandidate]:
    relationship_candidates: list[RelationshipCandidate] = []

    for occurrence in relationships:
        relationship = occurrence.relationship
        chunk_id = occurrence.evidence.chunk_id

        source_reference = (
            chunk_id,
            _local_id_key(relationship.source_entity_id),
        )

        target_reference = (
            chunk_id,
            _local_id_key(relationship.target_entity_id),
        )

        source_entity_id = entity_id_by_local_reference.get(
            source_reference
        )
        target_entity_id = entity_id_by_local_reference.get(
            target_reference
        )

        # Endpoint không tồn tại sau entity processing.
        if source_entity_id is None or target_entity_id is None:
            continue

        was_merged = False

        for index, candidate in enumerate(relationship_candidates):
            is_same_relationship = (
                candidate.source_entity_id == source_entity_id
                and candidate.target_entity_id == target_entity_id
                and candidate.relation_type == relationship.relation_type
            )

            if is_same_relationship:
                relationship_candidates[index] = merge_relationship(
                    current_relationship=occurrence,
                    target=candidate,
                )

                was_merged = True
                break

        if not was_merged:
            relationship_candidates.append(
                RelationshipCandidate(
                    source_entity_id=source_entity_id,
                    target_entity_id=target_entity_id,
                    relation_type=relationship.relation_type,
                    chunk_evidences=[occurrence.evidence],
                )
            )

    return relationship_candidates


def dedup_entities_and_relationships(
    validated_ontologies: list[ValidatedChunkResult],
):
    entity_occurrences: list[EntityOccurrence] = []
    relationship_occurrences: list[RelationshipOccurrence] = []

    for ontology in validated_ontologies:
        if ontology.is_skipped:
            continue

        for entity in ontology.valid_entities:
            entity_occurrences.append(
                EntityOccurrence(
                    entity=entity,
                    evidence=ChunkEvidence(
                        database_id=ontology.database_id,
                        chunk_id=ontology.chunk_id,
                        document_id=ontology.document_id,
                        description=entity.description,
                    ),
                )
            )

        for relationship in ontology.valid_relationships:
            relationship_occurrences.append(
                RelationshipOccurrence( 
                    relationship=relationship,
                    evidence=ChunkEvidence(
                        database_id=ontology.database_id,
                        chunk_id=ontology.chunk_id,
                        document_id=ontology.document_id,
                        description=relationship.description,
                    ),
                )
            )

    (entity_candidates, entity_id_by_local_reference) = dedup_entities(entity_occurrences)
    relationship_candidates = dedup_relationships(relationship_occurrences, entity_id_by_local_reference)
    return entity_candidates, relationship_candidates
    
## TEST    
# e = ExtractedEntity(
#     canonical_name="Trái mận",
#     aliases=["Trái roi"],
#     type="OBJECT",
#     description="Một loại trái thơm ngọt",
# )

# e2 = ExtractedEntity(
#     canonical_name="Trái roi",
#     aliases=["Trái mận"],
#     type="OBJECT",
#     description="Một loại trái chấm muối",
# )

# a = EntityOccurrence(
#     entity=e,
#     evidence=ChunkEvidence(
#         database_id=1,
#         chunk_id="test_chunk_1",
#         document_id="test_document",
#         description=e.description,
#     ),
# )

# b = EntityCandidate(
#     entity_id="new_entity",
#     canonical_name=e2.canonical_name,
#     aliases=e2.aliases,
#     observed_types=[e2.type],
#     chunk_evidences=[
#         ChunkEvidence(
#             database_id=2,
#             chunk_id="test_chunk_2",
#             document_id="test_document",
#             description=e2.description,
#         )
#     ],
# )

# print(check_reciprocal_names(a, b))
# # True