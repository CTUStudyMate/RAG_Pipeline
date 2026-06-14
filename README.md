# Multimodal RAG Pipeline

A Retrieval-Augmented Generation (RAG) pipeline for multimodal documents (PDFs + images). This repository contains the full pipeline from ingesting, parsing, chunking, retrieval, answer generation, to citation validation. The code includes different chunking strategies (fixed size, HSF (Hierarchical - Semantic - FixedSize), and LangChain-based recursive character text splitter) as well as retrieval strategies (vector-based and hybrid multistage).

---

## Project Structure

| Path | Description |
|------|-------------|
| `src/PIPELINE/` | Contains each step of the RAG pipeline. For every step, code for different strategies is organized here. |
| `src/app/` | Code for building the server with a complete end-to-end workflow. Uses a graph structure to call the selected strategies from PIPELINE and connect them into a chatflow. |
| `EXPERIMENTS/chunk_versions/` | Stores the output of different chunking strategies. The config file path in `pipeline_config.py` can be updated to point to the corresponding chunk data here, which is then used in downstream steps such as retrieval and generation. |
| `EXPERIMENTS/full_pipeline_strategies/` | Contains code and results from experiment runs with various configurations, from chunking through retrieval strategies. |
| `data/parsed_cache/` | Stores data parsed from PDF files. This cache is reused to run different chunking strategies without re-parsing the source documents. |

---

## Chunking Strategies

### HSF (Hierarchical - Semantic - FixedSize) — Primary Strategy

HSF is the primary chunking strategy and is used in the main application. This method:

- Supports chunking on very large documents.
- Preserves the **document hierarchy tree** and **semantic meaning**.
- Maintains **multimodal features** — a chunk can contain text, tables, and images.

Source code: `src/PIPELINE/_3_chunk/strategies/HSF/`

### Multistage Retrieval — Under Evaluation

The multistage retrieval method is currently being evaluated for integration into the app alongside HSF chunking. The pipeline consists of three steps:

1. **Vector Search + Text Search**
2. **Reranker**
3. **Cross-Encoder**

---

## Requirements

- Python 3.10+
- Tesseract *(optional, for OCR)*
- PostgreSQL with the **ParadeDB** extension running in Docker

### Install Python packages

```bash
pip install -r requirements.txt
```

If no `requirements.txt` is available, the main packages used include:

```
unstructured        # PDF partitioning
langchain-core
langchain-ollama
langchain-chroma    # or Chroma DB SDK
python-dotenv
tqdm
```

---

## Environment Variables

Create a `.env` file at the project root (refer to `env.example`):

```env
# Required
EMBEDDING_MODEL=<your-embedding-model>   # e.g., ollama model name
LLM=<your-llm-model>                     # e.g., gemma3:27b-cloud


---

## Quickstart

**1. Create and activate a virtual environment:**

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
```

**2. Install dependencies:**

```bash
pip install -r requirements.txt
```

**3. Set up PostgreSQL with ParadeDB:**

```bash
docker pull paradedb/paradedb
```

**4. Configure the environment and database:**

- Copy `env.example` to `.env` and fill in the required fields.
- Run the database initialization script inside the Docker container.

---

## License & Credits

This repository was developed as part of a thesis/work project. See authorship and academic usage notes in `docs/` if provided.

---

