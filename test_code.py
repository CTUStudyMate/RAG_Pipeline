from PIPELINE._3_knowledge_graph.ontology_handler.helpers import _normalize_text
from rapidfuzz import fuzz
import re

def normalize_text(text):
    text = re.sub(r'[^\w\s]', '', text.lower())
    return ' '.join(text.split())  

def is_fuzzy_match(text1: str, text2: str, threshold: float = 90) -> bool:
    score = fuzz.ratio(text1, text2)
    return score

print(is_fuzzy_match(normalize_text("Object-Orriented Programming"), normalize_text("Object orriented programming")))