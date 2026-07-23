import csv
import json
import time
from pathlib import Path

from PIPELINE._4_retrieve.multi_stages.normal_retriever import normal_retrieve


PROJECT_ROOT = Path(__file__).resolve().parents[3]
INPUT_FILE = PROJECT_ROOT / "studyguide_based_dataset.json"
OUTPUT_FILE = Path(__file__).resolve().parent / "hsf_normal_retrieve_only_studyguide.csv"


def load_questions(json_file):
    with Path(json_file).open(mode="r", encoding="utf-8") as f:
        data = json.load(f)

    return [item["question"] for item in data]


def build_embedded_text(docs):
    """Build the retrieved text in the same format as build_content_inputs."""
    embedded_parts = []

    for i, doc in enumerate(docs):
        metadata = doc.get("metadata", {})
        embedded_content = metadata.get("embeded_content", "")
        embedded_parts.append(f"\n[{i}]\n{embedded_content}\n")

    return "\n".join(embedded_parts)


def run_and_log(input_file=INPUT_FILE, output_file=OUTPUT_FILE):
    questions = load_questions(input_file)
    output_file = Path(output_file)
    file_exists = output_file.exists() and output_file.stat().st_size > 0

    with output_file.open(mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow(["question", "embedded_text", "retrieve_time_sec"])

        for q in questions:
            retrieve_start = time.perf_counter()
            docs = normal_retrieve(q)
            retrieve_elapsed = time.perf_counter() - retrieve_start

            embedded_text = build_embedded_text(docs)
            writer.writerow([q, embedded_text, round(retrieve_elapsed, 3)])
            f.flush()

            print(f"Done: {q[:200]} ({retrieve_elapsed:.2f}s)")


if __name__ == "__main__":
    run_and_log()
