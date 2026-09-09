# python -m src.PIPELINE._3_knowledge_graph.ontology_handler.ontology_extractor

from PIPELINE._3_knowledge_graph.ontology_handler.ontology_definition import ENTITY_TYPES, RELATION_TYPES
from pydantic import BaseModel, Field
from typing import get_args

from pipeline_setup import llm

# max_knowledge_triplets = 3
entity_types_text = ", ".join(get_args(ENTITY_TYPES))
relation_types_text = ", ".join(get_args(RELATION_TYPES))

prompt_template = f"""
-Goal-
Given the source text below, extract the entities and relationships explicitly supported by the text.

Do not use external knowledge or infer unsupported information.

-Allowed Entity Types-
{entity_types_text}

-Allowed Relationship Types-
{relation_types_text}

-Steps-
1. Identify the entities that are important for understanding the source text.

For each entity, extract:

- canonical_name:
  The clearest and most standard name of the entity, using normal capitalization.
  Use the same canonical name consistently throughout the output.

- aliases:
  Alternative names, abbreviations, acronyms, or spelling variants that explicitly refer to the same entity in the source text.
  Do not include the canonical name itself.
  Return an empty list if no aliases are present.

- type:
  Exactly one value from the allowed entity types.
  Use OTHER only when none of the more specific types apply.

- description:
  A concise, self-contained description of the entity, its relevant attributes, and its role in the source text.
  Include only information supported by the source text.

2. Identify relationships between the extracted entities.

Only extract a relationship when the source text clearly supports a meaningful
connection between the two entities.

For each relationship, extract:

- source:
  The exact canonical_name of the source entity identified in Step 1.

- target:
  The exact canonical_name of the target entity identified in Step 1.

- relation_type:
  Exactly one value from the allowed relationship types.
  Select the most specific applicable type.
  Use RELATED_TO only when the relationship is meaningful but no more specific
  allowed type applies.
  
- description:
  A concise sentence explaining how the source entity relates to the target entity
  according to the source text.

3. Apply the following consistency rules:

- Every relationship endpoint must correspond to an entity returned in Step 1.
- Use canonical_name, not an alias, in source and target.
- Do not create duplicate entities or duplicate relationships.
- Do not treat two aliases of the same entity as separate entities.
- Preserve relationship direction.
- Extract a relationship only when the source text explicitly states or clearly entails a specific connection between the two entities. Do not create a relationship merely because both entities appear in the same text.
- If no entities or relationships can be reliably extracted, return empty lists.
- Return all output fields in English.

-Source Text-
{{text}}
"""


class ExtractedEntity(BaseModel):
    canonical_name: str = Field(description="Name of the entity, capitalized")
    aliases: list[str] = Field(
        default_factory=list,
        description=(
            "Alternative names, abbreviations, acronyms, or spelling variants "
            "that refer to the same entity. Exclude the canonical name."
        ),)
    type: ENTITY_TYPES = Field(description="One of the allowed entity types")
    description: str = Field(description="Brief description of the entity and its role")

class ExtractedRelationship(BaseModel):
    source: str = Field(description="Name of the source entity")
    target: str = Field(description="Name of the target entity")
    relation_type: RELATION_TYPES = Field(description="Relationship type from source to target.")
    description: str = Field(description="Sentence explaining the relationship")
    # evidence_chunk_ids: list[str] = Field(description="IDs of the chunks that provide evidence for this relationship.")

class ExtractionResult(BaseModel):
    entities: list[ExtractedEntity] = Field(default_factory=list)
    relationships: list[ExtractedRelationship] = Field(default_factory=list)
    
def extract_ontology(text: str) -> ExtractionResult:
    if not text.strip():
        return ExtractionResult()
    return llm.generate_structured(system_prompt=prompt_template, content=text, response_model=ExtractionResult, reasoning_effort="medium")

sample_text = """
Object-oriented programming supports abstraction, inheritance, and polymorphism.
A subclass inherits attributes and methods from its superclass.
An object is an instance of a class.
Inheritance can enable polymorphic behavior through method overriding.
"""

result = extract_ontology(sample_text)

print(result.model_dump_json(indent=2))
    