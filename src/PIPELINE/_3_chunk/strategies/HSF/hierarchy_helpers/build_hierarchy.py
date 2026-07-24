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
def generate_smart_toc(doc):
    toc = []
    
    for i, page in enumerate(doc):
        blocks = page.get_text("dict")["blocks"]
        
        for b in blocks:
            if "lines" not in b:
                continue
                
            for line in b["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    size = span["size"]
                    
                    # heuristic: font lớn → heading
                    if size > 14 and len(text) < 100:
                        toc.append([1, text, i+1])
    
    return toc if toc else generate_smart_toc(doc)
    
def create_root_node():
    """Create the hierarchy root used when a document has no usable TOC."""
    return {
        "level": 0,
        "title": "ROOT",
        "children": []
    }


def dfs(toc):
    # Always return a valid tree.  The atomic parser appends document content to
    # the currently open node, so a root-only tree lets documents without a TOC
    # continue through the normal parsing/chunking flow.
    root = create_root_node()
    if not toc:
        return root

    stack = [root]
    for level, title, page in toc:
        node = make_node(level, title, page)
        while stack and stack[-1]["level"] >= level:
            stack.pop()
        stack[-1]["children"].append(node)
        stack.append(node)
        
    return root

def build_hierarchy(file_path: str):
    with fitz.open(file_path) as doc:
        try:
            toc = doc.get_toc()
        except Exception:
            # Some PDFs do not expose a readable outline/TOC.  In that case,
            # return a root-only hierarchy instead of aborting document upload.
            toc = []

    return dfs(toc)
