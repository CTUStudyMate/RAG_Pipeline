from used_models.llm.LLM_Factory import get_llm
from pipeline_config import settings
import psycopg
from pipeline_config import settings
from used_models.embeddings.embed_factory import EmbeddingService 
import chromadb

pgdb_connect_info = settings.pgdb_connect_info

conn = psycopg.connect(
host=pgdb_connect_info.host,
port=pgdb_connect_info.port,
dbname=pgdb_connect_info.db_name,
user=pgdb_connect_info.user,
password=pgdb_connect_info.password
)
cursor = conn.cursor()

llm = get_llm(provider=settings.config["llm_provider"])
model = llm.lcModel

PGDB_CONNECT_INFO = settings.pgdb_connect_info
EMBEDDING_PROVIDER = settings.config["embedding_provider"]
VECTORDB_CONNECT_INFO = settings.config["vectordb_connect_info"]

embedder = EmbeddingService(provider=EMBEDDING_PROVIDER)

_default_db_path = VECTORDB_CONNECT_INFO["db_path"]
_default_collection_name = VECTORDB_CONNECT_INFO["collection"]

_default_client = chromadb.PersistentClient(path=_default_db_path)
_default_collection = _default_client.get_or_create_collection(
    name=_default_collection_name
)
