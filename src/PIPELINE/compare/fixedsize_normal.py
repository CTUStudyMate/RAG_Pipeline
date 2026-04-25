import csv
import time
from pathlib import Path

from PIPELINE._4_retrieve.multi_stages.normal_retriever import normal_retrieve
from PIPELINE._5_generate.generate import generate_answer
from pipeline_config import VECTORDB_FIXEDSIZE_CONNECT_INFO


def load_questions(csv_file):
    questions = []
    
    with open(csv_file, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            questions.append(row["Question"])  # tên cột phải đúng chính tả
    
    return questions


def run_and_log(inputfile="./experiment_data/ts.csv", output_file="results.csv"):
    input_file = Path(inputfile)
    questions = load_questions(input_file)
    file_exists = Path(output_file).exists()
    with open(output_file, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow(["question", "context", "answer", "time_sec"])

        for q in questions:
            start = time.perf_counter()

            docs = normal_retrieve(q, VECTORDB_FIXEDSIZE_CONNECT_INFO)
            answer, context = generate_answer(q, docs)

            end = time.perf_counter()
            elapsed = end - start

            writer.writerow([q, context, answer, round(elapsed, 3)])

            print(f"Done: {q} ({elapsed:.2f}s)")

run_and_log("./experiment_data/questions_gradingnotes.csv","./experiment_data/fixedsize_normal_result_356.csv")            