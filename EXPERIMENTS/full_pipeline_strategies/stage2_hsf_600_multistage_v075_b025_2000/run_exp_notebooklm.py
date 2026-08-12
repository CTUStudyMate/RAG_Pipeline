import csv
import json
import time
from pathlib import Path

from PIPELINE._4_retrieve.multi_stages.multi_stages_retriever import multi_stages_retrieve
from PIPELINE._5_generate.generate import generate_answer
from PIPELINE._6_citation_postprocessing.validate_citation import (
    filter_segments,
    merge_segments_to_text,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
EXP_DIR = Path(__file__).resolve().parent
INPUT_QUESTIONS = PROJECT_ROOT / "notebooklm_generated_dataset.json"
STRATEGIES = ["multistage"]


def load_questions(json_file):
    with Path(json_file).open(mode="r", encoding="utf-8") as f:
        return [item["question"] for item in json.load(f)]


def run_and_log(chunk_retrieve_strategy, input_file, output_file):
    questions = load_questions(input_file)
    output_file = Path(output_file)
    file_exists = output_file.exists() and output_file.stat().st_size > 0

    with output_file.open(mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow([
                "question",
                "context",
                "initial_answer",
                "answer",
                "retrieve_time_sec",
                "generate_time_sec",
            ])

        for q in questions:
            match chunk_retrieve_strategy:
                case "multistage":
                    retrieve_start = time.perf_counter()
                    docs = multi_stages_retrieve(query=q)
                    retrieve_elapsed = time.perf_counter() - retrieve_start
                case _:
                    raise ValueError(
                        f"Unsupported retrieve strategy: {chunk_retrieve_strategy}"
                    )

            generate_start = time.perf_counter()
            answer, context, docs, embedded_text = generate_answer(query=q, docs=docs)
            generate_elapsed = time.perf_counter() - generate_start

            answer_segments = json.loads(answer)
            processed_segments = filter_segments(answer_segments, docs)
            final_answer = merge_segments_to_text(processed_segments)

            if final_answer == "":
                final_answer = (
                    "The chatbot can't answer this question. "
                    "Please try again with another question."
                )

            writer.writerow([
                q,
                embedded_text,
                answer,
                final_answer,
                round(retrieve_elapsed, 3),
                round(generate_elapsed, 3),
            ])
            f.flush()

            print(f"Done: {q[:200]} ({retrieve_elapsed + generate_elapsed:.2f}s)")


if __name__ == "__main__":
    for strategy in STRATEGIES:
        run_and_log(
            chunk_retrieve_strategy=strategy,
            input_file=INPUT_QUESTIONS,
            output_file=(
                EXP_DIR / "stage2_hsf_multistage_v075_b025_600_2000_notebooklm.csv"
            ),
        )
