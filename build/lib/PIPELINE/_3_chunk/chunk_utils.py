from pathlib import Path
import json
from docling_core.types.doc.document import DoclingDocument


def run_strategy_on_folder(folder, strategy):
    folder = Path(folder)

    for json_file in sorted(folder.glob("*.json")):
        with open(json_file, "r", encoding="utf-8") as f:
            doc_dict = json.load(f)
            docling_doc = DoclingDocument.model_validate(doc_dict)
            
            # handle strategy on this batch document


        