import json
from pathlib import Path
from docling_core.types.doc.document import DoclingDocument, RefItem
from docling_core.transforms.chunker.hierarchical_chunker import ChunkingDocSerializer

from pipeline_config import settings
CHUNK_MAX_TOKEN = settings.config["chunk_max_token"]
OVERLAP_TOKENS = settings.config["overlap_tokens"]

def fixed_estimated_token_chunk(text, max_tokens=CHUNK_MAX_TOKEN, overlap_tokens=OVERLAP_TOKENS):
    # convert token to character
    avg_chars_per_token = 3.56
    
    chunk_size = int(max_tokens * avg_chars_per_token)
    overlap_size = int(overlap_tokens * avg_chars_per_token)

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)

        step = chunk_size - overlap_size
        if step <= 0:
            step = chunk_size

        start += step

    return chunks


def fixed_size_document_split(folder, min_tokens=OVERLAP_TOKENS):
    folder = Path(folder)
    json_files = sorted(folder.glob("*.json"))
    total_batches = len(json_files)

    all_chunks = []
    open_chunk_text = ""  # giữ phần dư giữa các batch

    avg_chars_per_token = 3.56
    min_chars = int(min_tokens * avg_chars_per_token)

    for i, json_file in enumerate(json_files, start=1):
        print(f"Processing batch {i}/{total_batches}: {json_file.name}")

        with open(json_file, "r", encoding="utf-8") as f:
            doc_dict = json.load(f)
            batch_document = DoclingDocument.model_validate(doc_dict)

            serializer = ChunkingDocSerializer(doc=batch_document)
            full_text = serializer.serialize().text

            # nối với phần dư từ batch trước
            full_text = open_chunk_text + " " + full_text
            open_chunk_text = ""

            # chunk
            chunks = fixed_estimated_token_chunk(full_text)

            # xử lý chunk cuối
            if chunks:
                last_chunk = chunks[-1]

                if len(last_chunk) < min_chars:
                    open_chunk_text = last_chunk
                    chunks = chunks[:-1]  # bỏ chunk cuối

            all_chunks.extend(chunks)

    #xử lý phần dư cuối cùng
    if open_chunk_text:
        if len(open_chunk_text) >= min_chars:
            all_chunks.append(open_chunk_text)
        else:
            # nếu quá nhỏ → merge vào chunk cuối
            if all_chunks:
                all_chunks[-1] += " " + open_chunk_text
            else:
                all_chunks.append(open_chunk_text)

    return all_chunks
            
            
    