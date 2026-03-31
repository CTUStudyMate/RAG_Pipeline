import os
from dotenv import load_dotenv
from models import VectorDBConnectIfo
from models.PGDBConnectInfo import PGDBConnectInfo

load_dotenv()

OPENAI_EMBEDDING_MODEL="text-embedding-3-small"
EMBEDDING_PROVIDER="openai"

MAX_PAGES_PER_BATCH=15
WRITE_FILE_AFTER_N_STREAM_ELEMENTS=10
CHUNK_MAX_TOKEN=800
CHUNK_MIN_TOKEN=200
OVERLAP_TOKENS=50

IMAGE_TOKEN_ESTIMATE=300

CHUNK_FROM_ATOMIC_TEST_FILEPATH="exp/se3003/atomic_chunk.json"
TOKEN_TREE_TEST_FILEPATH="exp/se3003/token_tree.json"
FINAL_CHUNKS_TEST_FILEPATH="exp/se3003/final_chunksss.json"
STREAM_ELEMENTS_FILEPATH="exp/se3003/streams.json"
TREE_FILEPATH="exp/se3003/tree.json"

PGDB_HOST=os.getenv("PGDB_HOST")
PGDB_PORT=os.getenv("PGDB_PORT")
PGDB_NAME=os.getenv("PGDB_NAME")
PGDB_USER=os.getenv("PGDB_USER")
PGDB_PASSWORD=os.getenv("PGDB_PASSWORD")
PGDB_CHUNKS_TABLE=os.getenv("PGDB_CHUNKS_TABLE")

VECTOR_DB_PATH='chroma01_DB'
VECTOR_DB_COLLECTION='v1_hsf_built_in_corpus' 

# VECTOR_DB_PATH='data_test/chroma/hsf'
# VECTOR_DB_COLLECTION='v1_hsf_built_in_corpus_cosine' 

VECTORDB_CONNECT_INFO: VectorDBConnectIfo = {
    "db_path": VECTOR_DB_PATH,
    "collection": VECTOR_DB_COLLECTION
}

PGDB_CONNECT_INFO: PGDBConnectInfo = {
    "host" : PGDB_HOST,
    "port": PGDB_PORT,
    "db_name": PGDB_NAME,
    "user": PGDB_USER,
    "password": PGDB_PASSWORD,
    "table_name": PGDB_CHUNKS_TABLE
}


VECTOR_RETRIEVE_CHUNKS_LIMIT=50
TEXT_RETRIEVE_CHUNKS_LIMIT=50

RRF_RANKING_CONSTANT=60
RRF_TOP_K=30

FINAL_CHUNKS_NUM=10

MAX_IMAGES_PER_LLMCALL=3