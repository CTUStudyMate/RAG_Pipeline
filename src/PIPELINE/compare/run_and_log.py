import csv
import time
from pathlib import Path

from PIPELINE._4_retrieve.multi_stages.multi_stages_retriever import multi_stages_retrieve
from PIPELINE._4_retrieve.multi_stages.normal_retriever import normal_retrieve
from PIPELINE._5_generate.generate import generate_answer
from common_utils.debug import log_to_file
from pipeline_config import VECTORDB_FIXEDSIZE_CONNECT_INFO, VECTORDB_HSF_MS_CONNECT_INFO

def load_questions(csv_file):
    questions = []
    
    with open(csv_file, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            questions.append(row["Question"])  # tên cột phải đúng chính tả
    
    return questions


def run_and_log(chunk_retrieve_strategy, inputfile="./experiment_data/ts.csv", output_file="results.csv"):
    input_file = Path(inputfile)
    questions = load_questions(input_file)
    file_exists = Path(output_file).exists()
    with open(output_file, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow(["question", "context", "answer", "retrieve_time_sec", "generate_time_sec"])

        for q in questions:
            
            match chunk_retrieve_strategy:
                case "fixed_normal": # fixed size chunking, vector retrieve
                    retrieve_start = time.perf_counter()
                    docs = normal_retrieve(q, VECTORDB_FIXEDSIZE_CONNECT_INFO)
                    retrieve_end = time.perf_counter()
                    
                case "hsf_normal": # hsf chunking, vector retrieve
                    retrieve_start = time.perf_counter()
                    docs = normal_retrieve(q, VECTORDB_HSF_MS_CONNECT_INFO)  
                    retrieve_end = time.perf_counter()
                    
                case "hsf_multi": # hsf chunking, multistage retrieve
                    retrieve_start = time.perf_counter()
                    docs = multi_stages_retrieve(q)   
                    retrieve_end = time.perf_counter()
              
            # log_to_file("*************************")  
            # log_to_file(chunk_retrieve_strategy)
            # log_to_file(docs)
            # log_to_file("*************************")  
            # return      
            
            retrieve_elapsed = retrieve_end - retrieve_start   
            
            generate_start = time.perf_counter()
            answer, context = generate_answer(q, docs)
            generate_end = time.perf_counter()
            generate_elapsed = generate_end - generate_start

            writer.writerow([q, context, answer, round(retrieve_elapsed, 3), round(generate_elapsed, 3)])

            print(f"Done: {q} ({retrieve_elapsed+generate_elapsed:.2f}s)")

strategies = ["fixed_normal", "hsf_normal", "hsf_multi"]
exp_dir = "exp/se2004_fixed/exp_result4/"
input_questions= "./experiment_data/questions_gradingnotes.csv"

for strategy in strategies:
    run_and_log(inputfile=input_questions, output_file=f"{exp_dir}{strategy}.csv", chunk_retrieve_strategy=strategy)        
