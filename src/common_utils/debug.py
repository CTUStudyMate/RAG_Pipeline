from pipeline_config import settings
LOG_FILE = settings.config["log_file"]

def log_to_file(anything):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(str(anything) + "\n")