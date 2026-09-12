import re
from rapidfuzz import fuzz

def _normalize_text(value: str) -> str:
    """Normalize surrounding/repeated whitespace without changing display casing."""
    return re.sub(r"\s+", " ", value.strip())


def _singularize_last_word(name: str) -> str:
    """
    Conservative English singularization for the final word of an entity name.

    Examples:
        "Software Engineers" -> "Software Engineer"
        "Computer Systems" -> "Computer System"
        "Theories" -> "Theory"

    It intentionally avoids aggressive linguistic guessing.
    """
    match = re.search(r"([A-Za-z]+)$", name)
    if not match:
        return name

    word = match.group(1)
    lower_word = word.casefold()

    # Words ending in these forms are often already singular.
    if lower_word.endswith(("ss", "us", "is", "ics")):
        return name

    if lower_word.endswith("ies") and len(word) > 3:
        singular = word[:-3] + ("Y" if word[-3:].isupper() else "y")
    elif lower_word.endswith(("ches", "shes", "xes", "zes", "sses")):
        singular = word[:-2]
    elif lower_word.endswith("s") and not lower_word.endswith("ss"):
        singular = word[:-1]
    else:
        return name

    return name[:match.start(1)] + singular

def normalize_text(text: str) -> str:
    return _normalize_text(text).casefold()

def is_fuzzy_match(
    text1: str,
    text2: str,
    threshold: float = 90,
) -> bool:
    score = fuzz.ratio(
        normalize_text(text1),
        normalize_text(text2),
    )
    return score >= threshold