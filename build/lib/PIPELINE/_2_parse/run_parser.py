from src.PIPELINE._2_parse.parser import run_parser
from src.PIPELINE._1_ingest.ingest import file_path

import time

start = time.perf_counter()

run_parser(file_path)

end = time.perf_counter()
elapsed = end - start

with open("parser_time.log", "a", encoding="utf-8") as f:
    f.write(f"{file_path} | {elapsed:.2f} seconds\n")

