from pipeline_config import LOG_FILE

def log_to_file(anything):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(str(anything) + "\n")