from PIPELINE._3_knowledge_graph.ontology_handler.ontology_extractor import doucment_chunksbatch_to_ontologies, fetch_document_chunks
from PIPELINE._3_knowledge_graph.ontology_handler.ontology_validation import validate_ontologies
from pipeline_setup import pool
from pipeline_config import settings
chunks_table = settings.pgdb_connect_info.chunks_table

def proccess_fetched_chunks(rows, document_name):
	chunk_results = doucment_chunksbatch_to_ontologies(rows, document_name) # extract
	valid_ontologies = validate_ontologies(chunk_results)
	processed_list, failed_list = resolve_and_merge_to_graph(valid_ontologies)
 
	with pool.connection() as conn: # update psql state
		with conn.cursor() as cur:
			if processed_list:
				cur.execute(
				f"""
				UPDATE {chunks_table}
				SET metadata = jsonb_set(
					metadata,
					'{{graph_processed}}',
					'true'::jsonb,
					true
				)
				WHERE id = ANY(%s)
				""",
				(processed_list,)
			)
				
				if failed_list:
					cur.execute(
					f"""
					UPDATE {chunks_table}
					SET metadata = jsonb_set(
						metadata,
						'{{graph_attempt_count}}',
						to_jsonb(
							CASE
								WHEN metadata -> 'graph_attempt_count' IS NULL
								THEN 1
								ELSE (metadata ->> 'graph_attempt_count')::int + 1
							END
						),
						true
					)
					WHERE id = ANY(%s)
					""",
					(failed_list,)
				)
				
		conn.commit()

def ingest_document_into_graph(document_id, document_name, chunks_limit=20, max_attempt = 3):
	while True:
		rows = fetch_document_chunks(document_id=document_id, max_attempt=max_attempt, chunks_limit=chunks_limit)
		if len(rows) == 0:
			break
		proccess_fetched_chunks(rows, document_name)