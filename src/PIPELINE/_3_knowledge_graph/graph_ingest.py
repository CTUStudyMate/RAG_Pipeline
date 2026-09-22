import atexit
import json
import os

from PIPELINE._3_knowledge_graph.logger.GraphLogger import GraphPipelineLogger
from neo4j import Driver, GraphDatabase

from PIPELINE._3_knowledge_graph.element_handler.entity_resolver import (
    resolve_and_upsert_entites,
)
from PIPELINE._3_knowledge_graph.element_handler.relationship_resolver import (
    resolve_and_upsert_relationships,
)
from PIPELINE._3_knowledge_graph.ontology_handler.ontology_extractor import (
    ChunkExtractionResult,
    doucment_chunksbatch_to_ontologies,
    fetch_document_chunks,
)
from PIPELINE._3_knowledge_graph.ontology_handler.ontology_validator_resolver import (
    dedup_entities_and_relationships,
    validate_ontologies,
)

from pipeline_setup import pool
from pipeline_config import settings


# =========================================================
# PostgreSQL config
# =========================================================

chunks_table = settings.pgdb_connect_info.chunks_table


# =========================================================
# Neo4j config
# =========================================================

NEO4J_URI = os.environ["NEO4J_URI"]
NEO4J_USERNAME = os.environ["NEO4J_USERNAME"]
NEO4J_PASSWORD = os.environ["NEO4J_PASSWORD"]
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")


driver: Driver = GraphDatabase.driver(
    NEO4J_URI,
    auth=(
        NEO4J_USERNAME,
        NEO4J_PASSWORD,
    ),
)

# Không close driver sau mỗi query/batch.
# Chỉ close khi process/app kết thúc.
atexit.register(driver.close)


def load_ontologies_from_file(
    file_path: str = "test_ontologies.json",
) -> list[ChunkExtractionResult]:

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    extracted_list = [
        ChunkExtractionResult.model_validate(item)
        for item in data
    ]

    return extracted_list


def process_fetched_chunks(
    rows,
    document_name,
    batch_id: int,
    logger: GraphPipelineLogger,
    driver: Driver,
    database: str = NEO4J_DATABASE,
):
    # =====================================================
    # 1. Extract ontology
    # =====================================================

    chunk_results = doucment_chunksbatch_to_ontologies(
        rows=rows,
        document_name=document_name,
        batch_id=batch_id,
        logger=logger,
    )

    # TEST ONLY:
    # chunk_results = load_ontologies_from_file(
    #     "test_ontologies.json"
    # )


    # =====================================================
    # 2. Validate ontology results
    # =====================================================

    valid_ontologies, validation_failures = validate_ontologies(
        chunk_results=chunk_results,
        batch_id=batch_id,
        document_name=document_name,
        logger=logger,
    )

    failed_list = [
        failure.database_id
        for failure in validation_failures
    ]

    valid_database_ids = [
        result.database_id
        for result in valid_ontologies
    ]


    # =====================================================
    # 3. Dedup + upsert graph
    # =====================================================

    try:
        entities, relationships = dedup_entities_and_relationships(
            validated_ontologies=valid_ontologies,
            batch_id=batch_id,
            document_name=document_name,
            logger=logger,
        )

        entity_map = resolve_and_upsert_entites(
            entity_candidates=entities,
            driver=driver,
            database=database,
        )

        resolve_and_upsert_relationships(
            entity_map=entity_map,
            relationship_candidates=relationships,
            driver=driver,
            database=database,
        )

        processed_list = valid_database_ids

    except Exception as error:
        print(f"Graph processing failed: {error}")

        failed_list.extend(valid_database_ids)
        processed_list = []


    processed_list = list(
        dict.fromkeys(processed_list)
    )

    failed_list = list(
        dict.fromkeys(failed_list)
    )


    # =====================================================
    # 4. Update PostgreSQL processing state
    # =====================================================

    with pool.connection() as conn:
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
                    (processed_list,),
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
                                WHEN metadata -> 'graph_attempt_count'
                                     IS NULL
                                THEN 1
                                ELSE
                                    (
                                        metadata
                                        ->> 'graph_attempt_count'
                                    )::int + 1
                            END
                        ),
                        true
                    )
                    WHERE id = ANY(%s)
                    """,
                    (failed_list,),
                )

        conn.commit()

    return processed_list, failed_list



# =========================================================
# Ingest whole document
# =========================================================
def ingest_document_into_graph(
    document_id,
    document_name,
    chunks_limit=20,
    max_attempt=3,
    driver: Driver = driver,
    database: str = NEO4J_DATABASE,
):
    batch_id = 1

    logger = GraphPipelineLogger(
        enabled=True
    )

    while True:
        rows = fetch_document_chunks(
            document_id=document_id,
            max_attempt=max_attempt,
            chunks_limit=chunks_limit,
        )

        if len(rows) == 0:
            break

        processed_list, failed_list = process_fetched_chunks(
            rows=rows,
            document_name=document_name,
            batch_id=batch_id,
            logger=logger,
            driver=driver,
            database=database,
        )

        print(
            f"Graph batch {batch_id} finished: "
            f"{len(processed_list)} processed, "
            f"{len(failed_list)} failed."
        )

        batch_id += 1
        
def main():
    driver.verify_connectivity()
    print("Connected to Neo4j.")

    document_id = "1"
    document_name = "se_theory_practice.pdf"

    ingest_document_into_graph(
        document_id=document_id,
        document_name=document_name,
        chunks_limit=20,
        max_attempt=3,
        driver=driver,
        database=NEO4J_DATABASE,
    )


if __name__ == "__main__":
    main()