import csv
import json
from pathlib import Path

from PIPELINE._4_retrieve.multi_stages.hybrid_retriever import text_search, vector_search
import psycopg
from pipeline_config import settings


pgdb_connect_info = settings.pgdb_connect_info

conn = psycopg.connect(
    host=pgdb_connect_info.host,
    port=pgdb_connect_info.port,
    dbname=pgdb_connect_info.db_name,
    user=pgdb_connect_info.user,
    password=pgdb_connect_info.password,
    options="-c client_encoding=UTF8"
)

cursor = conn.cursor()


def load_questions(json_file):
    with open(json_file, mode="r", encoding="utf-8") as f:
        data = json.load(f)
    return [item["question"] for item in data]


# =========================
# EXTRACT VECTOR SCORES
# =========================
def extract_vector_distances(results):
    """
    raw cosine distance from Chroma
    """
    if not results:
        return []

    if isinstance(results, dict):
        if "distances" in results and results["distances"]:
            return results["distances"][0]

    return []

def convert_to_similarity(distances):
    return [1 - d for d in distances] if distances else []


# =========================
# EXTRACT BM25 SCORES
# =========================
def extract_bm25_scores(rows):
    """
    row format:
    (id, document_id, text_content, metadata, score)
    """
    scores = []
    for r in rows:
        try:
            scores.append(r[4])  # paradedb.score(id)
        except Exception:
            continue
    return scores


# =========================
def run_and_log(inputfile, output_file="results.csv"):
    input_file = Path(inputfile)
    questions = load_questions(input_file)

    file_exists = Path(output_file).exists()

    with open(output_file, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow([
                "question",
                "vector_distances",
                "vector_scores",
                "bm25_scores"
            ])

        for q in questions:
            # ===== VECTOR SEARCH =====
            vector_results = vector_search(query=q)

            vector_distances = extract_vector_distances(vector_results)
            vector_scores = convert_to_similarity(vector_distances)

            # ===== BM25 SEARCH =====
            bm25_results = text_search(query=q, cursor=cursor)
            bm25_scores = extract_bm25_scores(bm25_results)

            # ===== WRITE =====
            writer.writerow([
                q,
                json.dumps(vector_distances, ensure_ascii=False),
                json.dumps(vector_scores, ensure_ascii=False),
                json.dumps(bm25_scores, ensure_ascii=False)
            ])

            print(f"Done: {q[:120]}...")

    


# =========================
# RUN
# =========================
exp_dir = "./"
# input_questions = "./experiment_data/eliminate_set.json"

# run_and_log(
#     inputfile=input_questions,
#     output_file=f"{exp_dir}_eliminate_score_result.csv"
# )

# input_questions = "./experiment_data/consider_set.json"
input_questions = "./experiment_data/safe_set.json"

run_and_log(
    inputfile=input_questions,
    output_file=f"{exp_dir}_safe_score_result.csv"
)

conn.close()