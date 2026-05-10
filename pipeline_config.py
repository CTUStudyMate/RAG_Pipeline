import os
from dotenv import load_dotenv
from src.models import VectorDBConnectIfo
from src.models.PGDBConnectInfo import PGDBConnectInfo

load_dotenv()
######### MODELS ##############
# EMBEDDING_PROVIDER="bge"
BGE_EMBEDDING_MODEL="bge-m3:latest"
EMBEDDING_PROVIDER="openai"
OPENAI_EMBEDDING_MODEL="text-embedding-3-small"

# LLM_PROVIDER="ollama"
# LLM_MODEL="qwen3.5:cloud"
LLM_PROVIDER="openai"
LLM_MODEL="gpt-4.1-mini"

# common
MAX_PAGES_PER_BATCH=15
# WRITE_FILE_AFTER_N_STREAM_ELEMENTS=10
WRITE_FILE_AFTER_N_STREAM_ELEMENTS=100
WRITE_FILE_AFTER_MAX_STREAM_ELEMENTS=200
CHUNK_MAX_TOKEN=600
CHUNK_MIN_TOKEN=200
OVERLAP_TOKENS=80

IMAGE_TOKEN_ESTIMATE=300
TOKEN_BUDGET=2000

####### store and debug ##################
CHUNK_FROM_ATOMIC_TEST_FILEPATH="exp/se2004_fixed/atomic_chunk.json"
TOKEN_TREE_TEST_FILEPATH="exp/se2004_fixed/token_tree.json"
FINAL_CHUNKS_TEST_FILEPATH="exp/se2004_fixed/final_chunksss.json"
STREAM_ELEMENTS_FILEPATH="exp/se2004_fixed/streams.json"
TREE_FILEPATH="exp/se2004_fixed/tree.json"
CHUNKING_TIME_LOG_FILE="exp/se2004_fixed/hsf_chunk_time.txt"
##########################################


PGDB_HOST=os.getenv("PGDB_HOST")
PGDB_PORT=os.getenv("PGDB_PORT")
PGDB_NAME=os.getenv("PGDB_NAME")
PGDB_USER=os.getenv("PGDB_USER")
PGDB_PASSWORD=os.getenv("PGDB_PASSWORD")


# fixed size chunk 
PGDB_FIXEDSIZE_NORMAL_CHUNKS_TABLE=os.getenv("PGDB_FIXEDSIZE_NORMAL_CHUNKS_TABLE")
PGDB_FIXED_SIZE_CONNECT_INFO: PGDBConnectInfo = {
    "host" : PGDB_HOST,
    "port": PGDB_PORT,
    "db_name": PGDB_NAME,
    "user": PGDB_USER,
    "password": PGDB_PASSWORD,
    "table_name": PGDB_FIXEDSIZE_NORMAL_CHUNKS_TABLE
}

# CHUNK_STORAGE_DIR='experiment_chunk_storage/v4_2004/'
CHUNK_STORAGE_DIR='experiment_chunk_storage/v4_2004_fixed/'

VECTOR_DB_FIXEDSIZE_PATH=f"{CHUNK_STORAGE_DIR}fixed_size"
VECTOR_DB_FIXEDSIZE_COLLECTION='v2004_fixedsize_built_in_corpus' 

VECTORDB_FIXEDSIZE_CONNECT_INFO: VectorDBConnectIfo = {
    "db_path": VECTOR_DB_FIXEDSIZE_PATH,
    "collection": VECTOR_DB_FIXEDSIZE_COLLECTION
}
FIXEDSIZE_CHUNKING_TIME_LOG_FILE="exp/se2004_fixed/exp_result/fixed_chunk_time.txt"
#-------------


# hsf chunk
VECTOR_DB_HSF_PATH=f"{CHUNK_STORAGE_DIR}hsf"
VECTOR_DB_HSF_COLLECTION='v2004_hsf_built_in_corpus' 

VECTORDB_HSF_MS_CONNECT_INFO: VectorDBConnectIfo = {
    "db_path": VECTOR_DB_HSF_PATH,
    "collection": VECTOR_DB_HSF_COLLECTION
}

PGDB_HSF_MS_CHUNKS_TABLE=os.getenv("PGDB_HSF_MS_CHUNKS_TABLE")
PGDB_HSF_MS_CONNECT_INFO: PGDBConnectInfo = {
    "host" : PGDB_HOST,
    "port": PGDB_PORT,
    "db_name": PGDB_NAME,
    "user": PGDB_USER,
    "password": PGDB_PASSWORD,
    "table_name": PGDB_HSF_MS_CHUNKS_TABLE
}
HSF_CHUNKING_TIME_LOG_FILE="exp/se2004_fixed/exp_result/fixed_chunk_time.txt"
#----------

# langchain_recursive_char_spitter
VECTOR_DB_LC_RECUR_PATH=f"{CHUNK_STORAGE_DIR}lc_recur_char_split"
VECTOR_DB_LC_RECUR_COLLECTION='v2004_lc_recur_built_in_corpus' 

VECTORDB_LC_RECUR_CONNECT_INFO: VectorDBConnectIfo = {
    "db_path": VECTOR_DB_LC_RECUR_PATH,
    "collection": VECTOR_DB_LC_RECUR_COLLECTION
}
CHUNKING_TIME_LC_BASED_LOG_FILE="exp/langchain_based/RecursiveCharacterTextSplitter.txt"

PGDB_LC_RECUR_CHUNKS_TABLE=os.getenv("PGDB_LC_RECUR_CHUNKS_TABLE")
PGDB_LC_RECUR_CONNECT_INFO: PGDBConnectInfo = {
    "host" : PGDB_HOST,
    "port": PGDB_PORT,
    "db_name": PGDB_NAME,
    "user": PGDB_USER,
    "password": PGDB_PASSWORD,
    "table_name": PGDB_LC_RECUR_CHUNKS_TABLE
}


RRF_RANKING_CONSTANT=60

VECTOR_RETRIEVE_CHUNKS_LIMIT=30
TEXT_RETRIEVE_CHUNKS_LIMIT=30

RRF_TOP_K=20

FINAL_CHUNKS_NUM=7

MAX_IMAGES_PER_LLMCALL=3

LOG_FILE="./mylog6.txt"