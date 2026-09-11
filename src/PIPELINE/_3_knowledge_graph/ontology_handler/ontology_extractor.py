# python -m src.PIPELINE._3_knowledge_graph.ontology_handler.ontology_extractor

from PIPELINE._3_knowledge_graph.ontology_handler.ontology_definition import ENTITY_TYPES, RELATION_TYPES
from PIPELINE._3_knowledge_graph.ontology_handler.ontology_extraction_prompt import system_prompt_for_ontology_extraction, build_extraction_input
from pydantic import BaseModel, Field
from typing import Any

from pipeline_setup import llm, pool
from pipeline_config import settings
import re

chunks_table = settings.pgdb_connect_info.chunks_table

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

class LLMExtractionResult(BaseModel):
    should_extract: bool = Field(
        description=(
            "Whether the source contains substantive academic knowledge "
            "relevant to the document and suitable for extraction."
        )
    )

    skip_reason: str = Field(
        description=(
            "Brief reason for skipping the source. "
            "Return an empty string when should_extract is true."
        )
    )
    entities: list[ExtractedEntity] = Field(default_factory=list)
    relationships: list[ExtractedRelationship] = Field(default_factory=list)

class ChunkExtractionResult(BaseModel):
	database_id: Any
	chunk_id: str
	document_id: str
	ontology: LLMExtractionResult
	

def fetch_document_chunks(document_id, chunks_limit, max_attempt):
	with pool.connection() as conn:
		with conn.cursor() as cur:
			cur.execute(
				f"""
				SELECT id, metadata
				FROM {chunks_table}
				WHERE metadata ->> 'document' = %s
				AND (
					metadata -> 'graph_processed' IS NULL
					OR (metadata ->> 'graph_processed')::boolean = false
				)
				AND (
					metadata -> 'graph_attempt_count' IS NULL
					OR (metadata ->> 'graph_attempt_count')::int < %s
				)
				ORDER BY id
				LIMIT {chunks_limit}
				""",
				(str(document_id), max_attempt)
			)

			rows = cur.fetchall()
	return rows

def extract_ontology(text: str) -> LLMExtractionResult:
    if not text or not text.strip():
        return LLMExtractionResult(
            should_extract=False,
            skip_reason="Empty source content.",
            entities=[],
            relationships=[],
        )

    return llm.generate_structured(
        system_prompt=system_prompt_for_ontology_extraction,
        content=text,
        response_model=LLMExtractionResult,
        reasoning_effort="medium",
    )  
    
def doucment_chunksbatch_to_ontologies(rows, document_name)->  tuple[list[str], list[str]]:
    extracted_list = []
    for row in rows:
        metadata = row[1]
        input_for_extraction = build_extraction_input(metadata, document_name)
        print(f"Running extraction for {input_for_extraction[:200]} ... ")
        llm_extract_result = extract_ontology(input_for_extraction)
        extracted_result = ChunkExtractionResult(database_id=row[0], chunk_id=metadata["chunk_id"], document_id=metadata["document"], ontology=llm_extract_result)
        extracted_list.append(extracted_result)
    # with open("test_ontologies.json", "w", encoding="utf-8") as f:
    #     json.dump([item.model_dump() for item in extracted_list], f, ensure_ascii=False, indent=2)
    return extracted_list

        
#     Lấy 20 chunks
# → extract từng chunk
# → tạo list[ChunkExtractionResult]
# → resolve toàn bộ batch
# → đối chiếu với graph hiện có
# → ghi Neo4j
# → đánh dấu processed
# → lấy 20 chunks tiếp theo
	 




# chunks_limit = 10
# document_id = "1"
# max_attempt = 3

# import json
# with pool.connection() as conn:
#     with conn.cursor() as cur:
#         cur.execute(
#             f"""
#             SELECT id, metadata
#             FROM {chunks_table}
#             WHERE metadata ->> 'document' = %s
#               AND (
#                   metadata -> 'graph_processed' IS NULL
#                   OR (metadata ->> 'graph_processed')::boolean = false
#               )
#               AND (
#                   metadata -> 'graph_attempt_count' IS NULL
#                   OR (metadata ->> 'graph_attempt_count')::int < %s
#               )
#             ORDER BY id
#             LIMIT {chunks_limit}
#             """,
#             (str(document_id), max_attempt)
#         )

#         rows = cur.fetchall()

# data = [
#     {
#         "id": row_id,
#         "metadata": metadata
#     }
#     for row_id, metadata in rows
# ]

# with open(
#     "EXPERIMENTS/graph/v1/test_chunks.json",
#     "w",
#     encoding="utf-8"
# ) as f:
#     json.dump(
#         data,
#         f,
#         ensure_ascii=False,
#         indent=2
#     )

# #################### TEST
import json

with open(
	"EXPERIMENTS/graph/v1/test_chunks.json",
	"r",
	encoding="utf-8"
) as f:
	data = json.load(f)

rows = [
	(item["id"], item["metadata"])
	for item in data
]
rows = rows
doucment_chunksbatch_to_ontologies(rows=rows, document_name="Software Engineering - Theory and Practice")

pool.close() # không để dòng này chạy khi chạy rag server