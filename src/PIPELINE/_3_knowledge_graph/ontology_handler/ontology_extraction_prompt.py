import re
from typing import get_args
from PIPELINE._3_knowledge_graph.ontology_handler.ontology_definition import ENTITY_TYPES, RELATION_TYPES

entity_types_text = ", ".join(get_args(ENTITY_TYPES))
relation_types_text = ", ".join(get_args(RELATION_TYPES))
    
system_prompt_for_ontology_extraction = f"""
The provided source may contain TEXTUAL CONTENT, FIGURE DESCRIPTIONS, or both.

# Goal
	- Extract the IMPORTANT entities and relationships explicitly supported by either the textual content or the figure descriptions.
	- When textual content and figure descriptions express the same fact, extract it only once.
	- Do not use external knowledge or infer unsupported information.
	- Do not convert speculative visual statements expressed with words such as "appears", "suggests", or "may represent" into definite facts.

# Allowed entity types
    - CONCEPT: an abstract idea, category, theory, role, discipline, or principle.
    - OBJECT: an identifiable physical or digital thing that is not better modelled as an artifact or system.
    - METHOD: a repeatable technique, approach, algorithm, or prescribed way of doing something.
    - PROCESS: an activity or sequence of activities that unfolds over time.
    - SYSTEM: interacting components organized to achieve a function.
    - PROPERTY: a quality, attribute, condition, or measurable characteristic.
    - ARTIFACT: a human-created product, document, model, plan, or deliverable.
    - PERSON: a specific individual or a human actor explicitly treated as a person.
    - ORGANIZATION: a company, institution, team, department, or formal group.
    - LOCATION: a place or geographical area.
    - EVENT: a bounded occurrence in time.
    - OTHER: use only when none of the above is appropriate.
	
# Allowed relationship types
	{relation_types_text}

# Rules:
	
    - When the source explicitly states, defines, or clearly supports the full form of an abbreviation or acronym, use the full form as the canonical name and include the abbreviation or acronym as an alias.
        Example:
        Source: "Object-Oriented Programming (OOP) ..."
        canonical_name: "Object-Oriented Programming"
        aliases: ["OOP"]
    - Do not use external knowledge to expand an abbreviation or acronym. If the source does not provide or clearly support its full form, preserve the abbreviation or acronym as the canonical name rather than guessing an expansion.
    - Preserve the semantic head of a noun phrase. Preserve meaningful multi-word noun phrases as complete entities when the complete phrase plays a semantic role in a statement. Do not additionally extract a nested component of a compound entity merely because that component appears inside the phrase.
	- Every relationship endpoint must correspond to an entity returned in Step 1. Use local_id of the entity in source and target.
	- Do not create duplicate entities or duplicate relationships.
	- Do not treat two aliases of the same entity as separate entities.
	- Preserve relationship direction.
	- Extract a relationship only when the source text explicitly states or clearly entails a specific connection between the two entities. Do not create a relationship merely because both entities appear in the same text.
    - Do not extract both directions of the same semantic relationship. If one relationship already expresses the fact, do not add an inverse or reverse-direction version of that fact.
    - Do not replace a relationship target with a noun that appears only inside an "of", "about", or similar modifying phrase.
	- If no entities or relationships can be reliably extracted, return empty lists.
	- Return all output fields in English.
	
# Instructions

## Relevance decision

Before extracting, determine whether the source contains substantive academic knowledge relevant to the document or section.

Set should_extract to false for:
    - blank pages;
    - book covers and decorative images;
    - isolated titles, author affiliations, and edition information;
    - copyright, cataloging, publishing, and production information;
    - tables of contents without explanatory content;
    - content unrelated to the academic subject of the document;
    - visual descriptions whose purported academic meaning is only speculative.
    - containing factual and structurally rich information but the information is not relevant to the document's academic subject.

When should_extract is false:
    - provide a concise skip_reason;
    - return empty entities and relationships.

Do not treat statements containing words such as "appears", "suggests",
"possibly", or "may depict" as definite factual evidence.

## Follow the steps:

	1. Identify the entities that are important for understanding the source text.
	
	For each entity, extract:
    - local_id:
        A unique identifier for the entity within the current extraction result.
        Use sequential identifiers such as E1, E2, E3, and so on.
        Do not reuse the same local_id for different entities within one extraction result.
	
	- canonical_name:
        The clearest and most standard name of the entity. 
        Must preserve the semantic head explicitly expressed in the source. Do not remove the head noun when shortening or normalizing a name.
        Use the same canonical name consistently throughout the output.
	
	- aliases:
        Alternative names, abbreviations, acronyms, or spelling variants that explicitly refer to the same entity in the source text.
        For a countable common noun: The canonical_name must be singular. Include its plural form as an alias when a valid and distinct plural form exists.
        Do not include the extracted canonical name.
        Do not include the canonical_name itself or variants that differ only in capitalization or surrounding whitespace.
        Do not generate singular or plural variants for proper names, acronyms, uncountable nouns, or expressions whose number form is uncertain.
        Return an empty list if no aliases are present.
	
	- type:
        Exactly one value from the allowed entity types.
        Use OTHER only when none of the more specific types apply.
	
	- description:
        A concise, self-contained description of the entity, its relevant attributes, and its role in the source text.
        Include only information supported by the source text.
	
	2. Identify relationships between the extracted entities.
	
	Only extract a relationship when the source text clearly supports a meaningful connection between the two entities identified in Step 1.
	
	For each relationship, extract:
	
	- source_entity_id: The exact local_id of the source entity identified in Step 1.
	
	- target_entity_id: The exact local_id of the target entity identified in Step 1.
	
	- relation_type:
        Exactly one value from the allowed relationship types.
        Select the most specific applicable type.
        Use RELATED_TO only when the relationship is meaningful but no more specific
        allowed type applies.
	  
	- description: A concise sentence explaining how the source entity relates to the target entity according to the source text.
"""

def clean_text_for_extraction(embedded_text: str) -> str:
    if not embedded_text or not embedded_text.strip():
        return ""

    # Lấy phần sau [CONTENT].
    content_match = re.search(
        r"\[CONTENT\]\s*:?\s*",
        embedded_text,
        flags=re.IGNORECASE,
    )

    if content_match:
        remaining_text = embedded_text[content_match.end():]
    else:
        # Fallback nếu dữ liệu không có marker [CONTENT].
        remaining_text = embedded_text

    # Tách textual content và figure descriptions.
    figure_parts = re.split(
        r"\[FIGURE_DESCRIPTIONS\]\s*:?",
        remaining_text,
        maxsplit=1,
        flags=re.IGNORECASE,
    )

    textual_content = figure_parts[0].strip()

    figure_descriptions = (
        figure_parts[1].strip()
        if len(figure_parts) > 1
        else ""
    )

    # Xóa các chỉ mục [0], [1], ... ở đầu dòng mô tả hình.
    figure_descriptions = re.sub(
        r"(?m)^[ \t]*\[\d+\][ \t]*",
        "",
        figure_descriptions,
    )

    blocks: list[str] = []

    if textual_content:
        blocks.append(
            f"TEXTUAL CONTENT\n\n{textual_content}"
        )

    if figure_descriptions:
        blocks.append(
            f"FIGURE DESCRIPTIONS\n\n{figure_descriptions}"
        )

    text = "\n\n".join(blocks)

    # Xóa khoảng trắng thừa cuối dòng.
    text = re.sub(r"[ \t]+\n", "\n", text)

    # Không để quá hai newline liên tiếp.
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()

def build_extraction_input(
    metadata: dict,
    document_name: str,
) -> str:
    embedded_text = metadata.get("embeded_content", "")
    extraction_source = clean_text_for_extraction(embedded_text)
    section = metadata.get("section", "Unknown section")

    return f"""
<DOCUMENT_CONTEXT>
Document: {document_name}
Section: {section}
</DOCUMENT_CONTEXT>

<SOURCE_CONTENT>
{extraction_source or "(empty)"}
</SOURCE_CONTENT>
""".strip()
