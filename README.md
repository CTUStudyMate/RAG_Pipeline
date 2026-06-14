# Multimodal RAG Pipeline

A Retrieval-Augmented Generation (RAG) pipeline for multimodal documents (PDFs + images). This repository contains the pipeline for RAG from ingesting → parsing → chunking → retrieve → generate answer and validate citation. The code includes different chunking strategies (including fixed size, HSF (Hierarchical - Semantic - FixedSize) and LangChain-based recursive character text splitter), with retrieve strategies (vector-based, hybrid multistage).

---

## 📁 Project Structure

| Path | Description |
|------|-------------|
| `src/PIPELINE/` | Trình bày các bước của RAG pipeline. Trong mỗi bước, code cho các strategies khác nhau được tổ chức tại đây. |
| `src/app/` | Code để build server với luồng hoạt động hoàn chỉnh. Sử dụng graph và gọi lại các strategies được chọn trong PIPELINE để nối thành chatflow. |
| `EXPERIMENTS/chunk_versions/` | Lưu kết quả của các chiến lược chunk khác nhau. Có thể thay đổi địa chỉ file config trong `pipeline_config.py` để trỏ đến dữ liệu chunk tương ứng — dữ liệu này sẽ được dùng cho các bước retrieve và generate. |
| `EXPERIMENTS/full_pipeline_strategies/` | Chứa code và kết quả của các lần chạy thực nghiệm với các config khác nhau, từ chunk đến chiến lược retrieve. |
| `data/parsed_cache/` | Chứa dữ liệu được parse từ file PDF. Dữ liệu này được tái sử dụng để chạy các chiến lược chunking khác nhau mà không cần parse lại document. |

---

## 🧩 Chunking Strategies

### HSF (Hierarchical - Semantic - FixedSize) — *Primary Strategy*

HSF là chiến lược chunking trọng tâm và được sử dụng trong ứng dụng chính. Phương pháp này:

- Hỗ trợ chunking trên các tài liệu rất lớn.
- Giữ nguyên **document hierarchy tree** và **semantic meaning**.
- Duy trì **multimodal feature** — một chunk có thể chứa cả văn bản, bảng và hình ảnh.

📂 Source code: `src/PIPELINE/_3_chunk/strategies/HSF/`

### Multistage Retrieval — *Đang xem xét*

Phương pháp retrieve multistage đang được đánh giá kết quả để tích hợp vào app cùng HSF chunk. Pipeline gồm 3 bước:

1. **Vector Search + Text Search**
2. **Reranker**
3. **Cross-Encoder**

---

## ⚙️ Requirements

- Python 3.10+
- Tesseract *(optional, for OCR)*
- PostgreSQL với **ParadeDB** extension chạy trong Docker

### Install Python packages

```bash
pip install -r requirements.txt
```

Nếu không có `requirements.txt`, các packages chính bao gồm:

```
unstructured        # PDF partitioning
langchain-core
langchain-ollama
langchain-chroma    # or Chroma DB SDK
python-dotenv
tqdm
```

---

## 🔑 Environment Variables

Tạo file `.env` tại thư mục gốc của project (tham khảo `env.example`):

```env
# Required
EMBEDDING_MODEL=<your-embedding-model>   # e.g., ollama model name
LLM=<your-llm-model>                     # e.g., gemma3:27b-cloud

# Optional
LLM2=<backup-llm-or-other-model>
CHUNK_MAX_CHARS=2000
CHUNK_AFTER_NCHARS=1500
CHUNK_COMBINE_UNDER_NCHARS=1000
MAX_IMAGES_PER_REQUEST=3
MAX_SUMMARY_INPUT_CHARS=3000
```

---

## 🚀 Quickstart

**1. Tạo và kích hoạt virtual environment:**

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
```

**2. Cài đặt dependencies:**

```bash
pip install -r requirements.txt
```

**3. Cài đặt PostgreSQL với ParadeDB:**

```bash
# Kéo Docker image có extension ParadeDB
docker pull paradedb/paradedb
```

**4. Cấu hình environment và database:**

- Tạo file `.env` từ `env.example` và điền các trường còn thiếu.
- Chạy script khởi tạo database trong container Docker.

---

## 📄 License & Credits

This repository was developed as part of a thesis/work project. See authorship and academic usage notes in `docs/` if provided.

---

## ❓ Questions & Support

For help tailoring this pipeline to your deployment, open an issue or discussion with details about your environment:

- **Deployment target:** Local / Cloud / Docker
- **LLM backend:** Ollama / HuggingFace / OpenAI-compatible API
- **Whether a `requirements.txt` needs to be generated**
