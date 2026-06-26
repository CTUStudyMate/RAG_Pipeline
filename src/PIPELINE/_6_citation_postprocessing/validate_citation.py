from used_models.schema.NormalizedChunk import NormalizedChunk
from rapidfuzz import fuzz, process
from difflib import SequenceMatcher
from transformers import pipeline
import re

# nli = pipeline("text-classification", model="roberta-large-mnli")

def normalize_text(text):
    text = re.sub(r'[^\w\s]', '', text.lower())
    return ' '.join(text.split())  


  # [
    #     {
    #         segment: claim,
    #         type: cited,
    #         citation: [
    #             {
    #                 text: text chính xác từ tài liệu,
    #                 chunk_id: chunk_id nó thuộc về,
    #                 cite_mark: mark cite của nó trong câu trả lời
    #             }
    #         ]
    #     },
    #            {
    #         segment: claim,
    #         type: inferred,
    #         citation: [inferred thì không có citation]
    #     }
    # ]
    
def filter_segments(segments, context_chunks):
    """
    Drop out the segments that are servere grounding error (invalid citation, mismatch citation)
    and return the processed segments for  UI rendering or final answer synthesizing
    """
    if len(segments) == 1 and segments[0].get("type") == "abstained":
        return segments
    valid_segments = []
    for segment in segments:
        result = validate_segment_citation(segment, context_chunks)

        if result:
            valid_segments.append(result)

    types = {segment.get("type") for segment in valid_segments}

    if types == {"intro"}:
        return []

    return valid_segments       
  


            
# {
#             "role": "paragraph" | "bullet_intro" | "bullet",
#             "segment": "one factual claim",
#             "citations": [
#                 {
#                     "type": "source_text",
#                     "content": "exact verbatim supporting text from the context",
#                     "img_id": null
#                 },
#                 {
#                     "type": "img",
#                     "content": null,
#                     "img_id": "image_0_1"
#                 }
#             ]
#         }
            
def validate_segment_citation(segment, docs):
    # Trả về segment với loại cite của nó (cited/inferred/intro (không cần cite))
    # Các cite đã được lọc lại và kiểm tra độ support với segment
        # nếu cite là img thì chỉ kiểm tra xem img_id có hợp lệ không
        # nếu cite là text thì merge hết các text lại và xem merged text này có support segment hay không
    citations = segment["citations"]
    valid_citations = []
    
    if not citations:
        if (segment["role"]) != "bullet_intro" and (segment["type"] == "abstained"):
            return {
                **segment
            }
        elif (segment["role"]) != "bullet_intro":
            return {
                **segment,
                "type": "inferred"
            } 
        else:
            return {
                **segment,
                "type": "intro"
            }  
    
    processed_cite_obj = {
        "texts": {},
        "images": {}
    }
    # filtered out the citations that are not in source
    for citation in citations:
        if citation["type"] == "img":
            img_cite_result = is_valid_img_citation(citation, docs)
            if img_cite_result:
                valid_citations.append({
                    **citation,
                    "processed_info": [img_cite_result]  # array, just to be similar to text parts
                })
                
        elif citation["type"] == "source_text":
            cite_text = citation["content"]  
            cite_result = is_cite_text_in_source(cite_text, docs)
            if cite_result: # if None, simply it's just not be added to the cite obj
                valid_citations.append({
                    **citation,
                    "processed_texts": cite_result #[(doc_id, cite_text_part)]
                })
    
    # if the segment has citations at first, but now the citations are empty, 
    # that segment is hallucinated and should be obmit
    if not valid_citations: # => cái này đổi thành check obj không có giá trị text hay img nào
        return None
    
    # check citation support (only for text) bây giờ không hợp tại mấy con nli yếu quá
    
    # for citation in valid_citations:
    #     if citation["type"] == "source_text":
    #         processed_texts = citation["processed_texts"]
    #         premise = " ... ".join(text for _, text in processed_texts)
    #         hypo = segment["segment"]
            
    #         print(premise)
    #         print(hypo)
    #         result = nli({
    #             "text": hypo,
    #             "text_pair": premise
    #         })
    #         print(result)
    
    # processed for UI rendering
    for citation in valid_citations:
        if citation["type"] == "source_text":
            processed_texts = citation["processed_texts"]
            for chunk_id, text_part in processed_texts:
                processed_cite_obj["texts"].setdefault(chunk_id, []).append(text_part)
        elif citation["type"] == "img":
            processed_infos = citation["processed_info"]
            for chunk_id, img_id in processed_infos:
                processed_cite_obj["images"].setdefault(chunk_id, []).append(img_id)    
    
    segment = {
        **segment,
        "processed_cite_obj": processed_cite_obj,
        "citations": valid_citations,
        "type": "cited"
    }  
    return segment      

                
def is_valid_img_citation(citation, docs):
    img_id = citation.get("img_id")
    # loop qua từng doc, nếu gặp id thì lưu vô obj
    # return None nếu id không tồn tại
    if img_id == "query_evidence":
        return (None, "query_evidence")
    for doc in docs:
        if "images" in doc["metadata"] and doc["metadata"]["images"]:
            images = doc["metadata"]["images"]
            if img_id in images:
                doc_id = doc["doc_id"]
                return (doc_id, img_id)
    return None        




def is_cite_text_in_source(cite_text: str, docs: list[NormalizedChunk]):
    # Split cite text by quoted parts ("...") to handle cases where
    # the LLM truncates or cuts citation text in the middle of quoted segments.
    # text_parts = [p.strip() for p in re.split(r'"(.*?)"', cite_text) if p.strip()]
    text_parts = [
        p.strip()
        for p in cite_text.split("...")
        if len(p.strip()) >= 5
    ]
    text_parts = [normalize_text(text_part) for text_part in text_parts]
    
    parts_and_chunks = [] # [(doc_id, the text part of the citation)]
    
    processed_docs = []
    for doc in docs:
        processed_docs.append({
            "doc_id": doc["doc_id"],
            "text": normalize_text(doc["text"])
        })

    # Loop through each split text part.
    # If any part is invalid, we immediately return None (strict validation rule:
    # all parts of the citation must be valid).
    for i, text_part in enumerate(text_parts):
        invalid_text = True

        # -------------------------
        # 1. Exact / substring match
        # -------------------------
        for doc in processed_docs:
            # Exact full match is unlikely due to LLM truncation,
            # so we use substring match instead.
            if text_part in doc["text"]:
                parts_and_chunks.append((doc["doc_id"], text_part))    
                invalid_text = False
                break  # exit exact match loop

        if not invalid_text:
            continue  # move to next text_part

        # -------------------------
        # 2. Fuzzy match fallback
        # -------------------------
        best_score = 0.0
        best_doc = None
        best_match_text = None

        for doc in docs:
            doc_text = doc["text"]
            result = fuzz.partial_ratio_alignment(text_part, doc_text)
            if result.score>best_score:
                best_score = result.score
                best_doc = doc["doc_id"]
                start = result.dest_start
                end = result.dest_end
                text = doc_text
                while end < len(text) and text[end] not in [" ", "_", "\n", "\t"]:
                    end += 1
                while start > 0 and text[start - 1] not in [" ", "_", "\n", "\t"]:
                    start -= 1    
                best_match_text = doc_text[start:end].strip()
            

        # If similarity is high enough, accept it
        if best_score > 80:             
            doc_id = best_doc
            parts_and_chunks.append((doc_id, best_match_text)) 
            invalid_text = False

        else:
            # If any part fails validation → entire citation is invalid
            return None

    return parts_and_chunks
        

def merge_segments_to_text(segments):
    """
    Merge structured segments into readable text for LLM evaluation.
    Rules:
    - sentence: inline
    - bullet_intro: newline (like section header)
    - paragraph: newline-separated blocks
    - bullet: each bullet on new line with "- "
    """

    parts = []
    current_line = ""

    def flush_line():
        nonlocal current_line
        if current_line.strip():
            parts.append(current_line.strip())
        current_line = ""

    for seg in segments:
        role = seg.get("role")
        text = seg.get("segment", "").strip()

        if not text:
            continue

        # -------------------------
        # paragraph → block
        # -------------------------
        if role == "paragraph":
            flush_line()
            parts.append(text)
            parts.append("")

        # -------------------------
        # sentence → inline
        # -------------------------
        elif role == "sentence":
            if current_line:
                current_line += " " + text
            else:
                current_line = text

        # -------------------------
        # bullet_intro → NEW LINE (header style)
        # -------------------------
        elif role == "bullet_intro":
            flush_line()
            parts.append(text)

        # -------------------------
        # bullet → list item
        # -------------------------
        elif role == "bullet":
            flush_line()
            parts.append(f"- {text}")

        # -------------------------
        # fallback
        # -------------------------
        else:
            if current_line:
                current_line += " " + text
            else:
                current_line = text

    flush_line()

    return "\n".join(parts).strip()