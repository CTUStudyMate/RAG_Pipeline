import re
def extract_first_sentence(text: str) -> str:
    text = text.strip()

    # Regex bắt câu kết thúc bằng . ! ?
    match = re.search(r'(.+?[.!?])(\s|$)', text)

    if match:
        return match.group(1).strip()

    # Nếu không tìm được câu hoàn chỉnh
    return text

def extract_first_list_item(text: str) -> str:
    lines = text.strip().splitlines()

    for line in lines:
        line = line.strip()
        if line.startswith(("-", "*", "•")):
            return line

    return lines[0] if lines else ""

def extract_id_unit(element):
    text = element.text.strip()

    if element.label.value == "list_item":
        return extract_first_list_item(text)

    return extract_first_sentence(text)