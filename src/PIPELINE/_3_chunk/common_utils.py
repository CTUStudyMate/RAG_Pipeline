# import tiktoken
# encoding = tiktoken.encoding_for_model("gpt-4o-mini")
import re
from pipeline_config import settings

CHUNK_MAX_TOKEN = settings.config["chunk_max_token"]
CHUNK_MIN_TOKEN = settings.config["chunk_min_token"]
OVERLAP_TOKENS = settings.config["overlap_tokens"]

def mannual_token_count(text):
    return max(1, int(len(text) / 3.56))

def split_sentences(text):
    return re.split(r'(?<=[.!?])\s+', text)

def get_overlap_tail(text, max_tokens):
    words = text.split()
    est_tokens_per_word = 1.3
    n_words = int(max_tokens / est_tokens_per_word)
    return " ".join(words[-n_words:]) if len(words) > n_words else text

def hard_split_sentence(sentence):
    words = sentence.split()
    segments = []
    current = ""

    for w in words:
        if mannual_token_count(current + " " + w) <= CHUNK_MAX_TOKEN:
            current += " " + w
        else:
            if current:
                segments.append(current.strip())
            current = w

    if current:
        segments.append(current.strip())

    return segments

def split_text(chunk_text):
    texts = []
    current_text = ""

    sentences = split_sentences(chunk_text)

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        #  Case 1: thêm sentence vẫn OK
        if mannual_token_count(current_text + " " + sentence) <= CHUNK_MAX_TOKEN:
            current_text += " " + sentence
            continue

        #  Case 2: vượt max → cần flush
        if mannual_token_count(current_text) >= CHUNK_MIN_TOKEN:
            texts.append([current_text.strip(), mannual_token_count(current_text)])

            # tạo overlap
            current_text = get_overlap_tail(current_text, OVERLAP_TOKENS)

        #  Case 3: current_text quá nhỏ (< MIN)
        else:
            # thử gộp luôn (nếu sentence không quá lớn)
            if mannual_token_count(sentence) <= CHUNK_MAX_TOKEN:
                current_text += " " + sentence
                texts.append([current_text.strip(), mannual_token_count(current_text)])
                current_text = get_overlap_tail(current_text, OVERLAP_TOKENS)
                continue

        # Case 4: sentence quá dài => hard split
        if mannual_token_count(sentence) > CHUNK_MAX_TOKEN:
            segments = hard_split_sentence(sentence)

            for seg in segments:
                if mannual_token_count(current_text + " " + seg) <= CHUNK_MAX_TOKEN:
                    current_text += " " + seg
                else:
                    if current_text:
                        texts.append([current_text.strip(), mannual_token_count(current_text)])
                        current_text = get_overlap_tail(current_text, OVERLAP_TOKENS)

                    current_text += " " + seg

    # push cuối
    if current_text:
        texts.append([current_text.strip(), mannual_token_count(current_text)])

    return texts


def print_splitted(texts):
    for text in texts:
        print("\n---")
        # print(text[0][:200])
        print(text)
        print(text[0][1])