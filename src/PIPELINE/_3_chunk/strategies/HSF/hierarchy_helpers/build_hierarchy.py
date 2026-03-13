import fitz
import re

def normalize_title(title: str) -> str:
    if not isinstance(title, str):
        return ""
    title = title.lower().strip()
    title = re.sub(r'^\d+(\.\d+)*\.?\s*', '', title)
    title = re.sub(r"[.,]", "", title)
    # remove space, tab, newline
    title = re.sub(r"\s+", "", title)
    return title

def make_node(level, title, page):
    return {
        "level": level,
        "title": normalize_title(title),
        "page": page,
        "children": []
    }
    
def dfs (toc):
    if not toc:
        return
    root = {
        "level": 0,
        "title": "ROOT",
        "children": []
    }
    stack = [root]
    for level, title, page in toc:
        node = make_node(level, title, page)
        while stack and stack[-1]["level"] >= level:
            stack.pop()
        stack[-1]["children"].append(node)
        stack.append(node)
        
    return root

def build_hierarchy(file_path: str):
    doc = fitz.open(file_path)
    toc = doc.get_toc()
    built_dfs = dfs(toc)
    return built_dfs