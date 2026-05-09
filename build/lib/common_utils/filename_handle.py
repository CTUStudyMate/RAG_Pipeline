import re
from pathlib import Path


def normalize_filename(file_path: str) -> str:
    """
    Convert file name into a safe folder name.

    - Remove extension
    - Remove dangerous characters
    - Replace spaces with underscore
    - Keep only alphanumeric, dash, underscore
    """

    name = Path(file_path).stem  # remove extension

    # lowercase
    name = name.lower()

    # replace spaces with _
    name = name.replace(" ", "_")

    # remove dangerous characters
    name = re.sub(r"[^\w\-]", "_", name)

    # collapse multiple underscores
    name = re.sub(r"_+", "_", name)

    # remove leading/trailing _
    name = name.strip("_")

    return name