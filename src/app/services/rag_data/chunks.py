import base64

from pipeline_setup import pool
from pipeline_config import settings
import psycopg

db_connect_info = settings.pgdb_connect_info

class DatabaseException(Exception):
    """General database error."""
    pass


class DatabaseConnectionException(DatabaseException):
    """Database connection failed."""
    pass


class ChunkNotFoundException(DatabaseException):
    """Requested chunk does not exist."""
    pass

class ImageNotFoundException(DatabaseException):
    """Requested img does not exist."""
    pass


def get_chunk_texts_from_db(chunk_ids: list[str]):
    table_name = db_connect_info.chunks_table

    query = f"""
        SELECT *
        FROM {table_name}
        WHERE document_id = ANY(%s)
    """

    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (chunk_ids,))
                rows = cur.fetchall()

    except psycopg.OperationalError as e:
        raise DatabaseConnectionException(
            "Cannot connect to database."
        ) from e

    except psycopg.Error as e:
        raise DatabaseException(
            "Database query failed."
        ) from e

    if not rows:
        raise ChunkNotFoundException(
            f"No chunks found for ids: {chunk_ids}"
        )

    return rows


def get_image_from_db(img_id):
    table_name = db_connect_info.images_table
    query = f"""
        SELECT *
        FROM {table_name}
        WHERE img_id = %s
    """
    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (img_id,))
                rows = cur.fetchone()
    
    except psycopg.OperationalError as e:
        raise DatabaseConnectionException(
            "Cannot connect to database."
        ) from e

    except psycopg.Error as e:
        raise DatabaseException(
            "Database query failed."
        ) from e

    if not rows:
        raise ImageNotFoundException(
            f"No images found for ids: {img_id}."
        )
    return rows            
    
# img = get_image_from_db(img_id="img0_se_theory_practice.pdf__chunk_0_0_0")
# print(img[2][:100])
# base64.b64decode(img[2])    