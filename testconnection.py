import psycopg
from pipeline_config import PGDB_CONNECT_INFO
import psycopg
import json

def index_to_pgdb(pgdb_connect_info, chunk_ids, chunk_text_contents, chunk_metadatas):
    conn = psycopg.connect(
        host=pgdb_connect_info["host"],
        port=pgdb_connect_info["port"],
        dbname=pgdb_connect_info["db_name"],
        user=pgdb_connect_info["user"],
        password=pgdb_connect_info["password"]
    )
    
    cur = conn.cursor()
    table_name = pgdb_connect_info["table_name"]

    # check length cho chắc
    if not (len(chunk_ids) == len(chunk_text_contents) == len(chunk_metadatas)):
        raise ValueError("Input lists must have same length")

    # convert metadata -> JSON string
    data = [
        (doc_id, text, json.dumps(meta))
        for doc_id, text, meta in zip(chunk_ids, chunk_text_contents, chunk_metadatas)
    ]

    cur.executemany(
        f"""
        INSERT INTO {table_name} (document_id, text_content, metadata)
        VALUES (%s, %s, %s)
        ON CONFLICT (document_id) DO NOTHING
        """,
        data
    )

    conn.commit()
    cur.close()
    conn.close()

# # Connect to ParadeDB
# conn = psycopg.connect(
#     host="localhost",
#     port=5433,
#     dbname="for_hybrid_search",
#     user="kt",
#     password="1223539654"
# )

# # Create a cursor
# cur = conn.cursor()

# # Test: select all rows
# cur.execute("SELECT id, content FROM documents LIMIT 5;")
# rows = cur.fetchall()

# for row in rows:
#     print(row)

# # Close
# cur.close()
# conn.close()
chunks_ids = ['1a']
chunk_text_contents = ['kt cute']
metadatas = [{'haha': '0123', 'hihi':'4567'}]
index_to_pgdb(pgdb_connect_info=PGDB_CONNECT_INFO, chunk_ids=chunks_ids, chunk_text_contents=chunk_text_contents, chunk_metadatas=metadatas)