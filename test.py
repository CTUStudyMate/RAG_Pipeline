import json

from common_utils.debug import log_to_file

from src.PIPELINE._4_retrieve.multi_stages.multi_stages_retriever import multi_stages_retrieve
from src.PIPELINE._5_generate.generate import generate_answer


with open("experiment_data/test_set.json", "r", encoding="utf-8") as f:
    questions = json.load(f)
print(len(questions))    

for question in questions:
    q = question["question"]
    docs = multi_stages_retrieve(q)
    answer, context = generate_answer(q, docs)
    log_to_file(answer)
    log_to_file(f"------{context}")
    log_to_file("\n\n*****************\n\n")