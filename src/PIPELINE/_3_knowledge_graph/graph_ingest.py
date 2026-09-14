from PIPELINE._3_knowledge_graph.ontology_handler.ontology_extractor import ChunkExtractionResult, doucment_chunksbatch_to_ontologies, fetch_document_chunks
from PIPELINE._3_knowledge_graph.ontology_handler.ontology_validator_resolver import dedup_entities_and_relationships, validate_ontologies
from pipeline_setup import pool
from pipeline_config import settings
chunks_table = settings.pgdb_connect_info.chunks_table

def resolve_and_merge_to_graph():
    # 1. Resolve EntityCandidate với entities đã có trong Neo4j.
# 2. Tạo mapping candidate entity_id → persistent Neo4j entity ID.
# 3. Remap source/target của RelationshipCandidate.
# 4. MERGE entity nodes.
# 5. MERGE relationship edges.
# 6. Merge chunk evidence.
# 7. Commit transaction.

# Neo4j transaction thành công
# → toàn bộ valid_ontologies được processed
#    kể cả skipped hoặc không có graph element

# Neo4j transaction thất bại
# → các non-skipped chunks cần graph write được failed

# validation_failures
# → tăng graph_attempt_count, không mark processed
	print("haha")

# def proccess_fetched_chunks(rows, document_name):
# 	chunk_results = doucment_chunksbatch_to_ontologies(rows, document_name) # extract
# 	valid_ontologies, validation_failures = validate_ontologies(chunk_results) # clean data in chunks
# 	entities, relationships = dedup_entities_and_relationships(valid_ontologies) 	
# 	graph_result = resolve_and_merge_to_graph(
# 		entities,
# 		relationships,
# 	)
 
# 	with pool.connection() as conn: # update psql state
# 		with conn.cursor() as cur:
# 			if processed_list:
# 				cur.execute(
# 				f"""
# 				UPDATE {chunks_table}
# 				SET metadata = jsonb_set(
# 					metadata,
# 					'{{graph_processed}}',
# 					'true'::jsonb,
# 					true
# 				)
# 				WHERE id = ANY(%s)
# 				""",
# 				(processed_list,)
# 			)
				
# 				if failed_list:
# 					cur.execute(
# 					f"""
# 					UPDATE {chunks_table}
# 					SET metadata = jsonb_set(
# 						metadata,
# 						'{{graph_attempt_count}}',
# 						to_jsonb(
# 							CASE
# 								WHEN metadata -> 'graph_attempt_count' IS NULL
# 								THEN 1
# 								ELSE (metadata ->> 'graph_attempt_count')::int + 1
# 							END
# 						),
# 						true
# 					)
# 					WHERE id = ANY(%s)
# 					""",
# 					(failed_list,)
# 				)
				
# 		conn.commit()

import json
from pathlib import Path


def load_ontologies_from_file(
    file_path: str = "test_ontologies.json"
) -> list[ChunkExtractionResult]:

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    extracted_list = [
        ChunkExtractionResult.model_validate(item)
        for item in data
    ]

    return extracted_list


def proccess_fetched_chunks(rows, document_name):
    # chunk_results = doucment_chunksbatch_to_ontologies(
    #     rows,
    #     document_name,
    # )  # extract
    
    chunk_results = chunk_results = load_ontologies_from_file("test_ontologies.json")

    valid_ontologies, validation_failures = validate_ontologies(
        chunk_results
    )  # clean data in chunks

    entities, relationships = dedup_entities_and_relationships(
        valid_ontologies
    ) # get final element list in the current batch

    output_data = {
        "entities": [
            entity.model_dump(mode="json")
            for entity in entities
        ],
        "relationships": [
            relationship.model_dump(mode="json")
            for relationship in relationships
        ],
        "validation_failures": [
            failure.model_dump(mode="json")
            if hasattr(failure, "model_dump")
            else failure
            for failure in validation_failures
        ],
    }

    output_path = Path(
        f"{document_name}_graph_elements.json"
    )
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            output_data,
            f,
            ensure_ascii=False,
            indent=2,
        )

    return entities, relationships

def ingest_document_into_graph(document_id, document_name, chunks_limit=20, max_attempt = 3):
	while True:
		rows = fetch_document_chunks(document_id=document_id, max_attempt=max_attempt, chunks_limit=chunks_limit)
		if len(rows) == 0:
			break
		proccess_fetched_chunks(rows, document_name)

# TEST
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
proccess_fetched_chunks(rows=rows, document_name="Sotware Engineering Theory and Practice")