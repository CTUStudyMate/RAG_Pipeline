import re
from thefuzz import fuzz

def normalize_docname(name: str) -> str:
    name = name.lower().strip()

    name = re.sub(r"\s+", "_", name)

    name = re.sub(r"[^a-z0-9_]", "", name)

    return name

def normalize_title(title: str) -> str:
    if not isinstance(title, str):
        return ""

    title = title.lower().strip()
    title = re.sub(r'^\d+(\.\d+)*\.?\s*', '', title)

    title = re.sub(r"[.,]", "", title)

    # remove space, tab, newline
    title = re.sub(r"\s+", "", title)

    return title


def is_heading_match(expected, actual):
    norm_exp = normalize_title(expected)
    norm_act = normalize_title(actual)
    if norm_exp == norm_act:
        return True
    if fuzz.token_sort_ratio(norm_exp, norm_act) >= 90:
        return True
    
    print("Heading processed but not match:")
    print("Norm expected:", norm_exp)
    print("Norm actual:", norm_act)
    return False

def is_title_match(ori_element, node):
    # match heading is the first requirement
    # next, the page must also match
    if not is_heading_match(ori_element.text, node["title"]):
        return False
    print("Matched title's text. Now check page....")
    print("Element is at page ", ori_element.prov[0].page_no)
    print("Title is at page ", node["page"])
    if (ori_element.prov[0].page_no == node["page"]):
        return True
    return False