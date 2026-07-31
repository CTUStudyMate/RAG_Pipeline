import sqlite3
from collections.abc import Callable

from PIPELINE._3_chunk.strategies.HSF.index_chunks import index_chunks
from PIPELINE._3_chunk.strategies.HSF.process_chunks import build_chunks
from pipeline_config import settings
from src.PIPELINE._3_chunk.strategies.HSF.process_atomics import process_atomics
from src.PIPELINE._3_chunk.strategies.HSF.process_token import compute_tree_token
from src.PIPELINE._1_ingest.ingest import file_path

PGDB_HSF_CONNECT_INFO = settings.pgdb_connect_info
VECTOR_DB_HSF_COLLECTION = settings.config["vectordb_connect_info"]["collection"]


def HSF_chunk(
    file_path: str,
    document_id: str,
    pgdb_connect_info=PGDB_HSF_CONNECT_INFO,
    on_before_index: Callable[[], None] | None = None,
) -> int:
    """Create and index HSF chunks while retaining MainBackend's document id."""
    hierarchy_tree, conn = process_atomics(file_path)

    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        compute_tree_token(hierarchy_tree, cursor)

        chunks = build_chunks(
            node=hierarchy_tree,
            file_path=file_path,
            cursor=cursor,
            prefix_path=document_id,
        )
        if not chunks:
            return 0

        if on_before_index is not None:
            on_before_index()

        index_chunks(
            chunks=chunks,
            collection_name=VECTOR_DB_HSF_COLLECTION,
            pgdb_connect_info=pgdb_connect_info,
        )
        return len(chunks)
    finally:
        conn.close()

# HSF_chunk(
#     file_path=file_path,
#     document_id="1",
#     pgdb_connect_info=PGDB_HSF_CONNECT_INFO
# )
