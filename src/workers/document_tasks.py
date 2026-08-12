"""Celery tasks for document ingestion."""

import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from src.clients.main_backend_client import MainBackendClient
from src.workers.celery_app import celery_app


logger = logging.getLogger(__name__)


CONFIG_OUTPUT_KEYS = (
    "log_file",
    "chunking_time_log_file",
    "chunk_from_atomic_test_filepath",
    "token_tree_test_filepath",
    "final_chunks_test_filepath",
    "stream_elements_filepath",
    "tree_filepath",
)


def mark_new_document_process(document_id: int, processing_run_id: str) -> Path | None:
    """Append a visible run boundary to every configured log and debug file."""
    from pipeline_config import settings

    marker = (
        f"\n\n{'=' * 80}\n"
        f"PROCESSING RUN START | document_id={document_id} "
        f"| processing_run_id={processing_run_id} "
        f"| started_at={datetime.now(timezone.utc).isoformat()}"
        f"\n{'=' * 80}\n"
    )

    output_paths = []
    for key in CONFIG_OUTPUT_KEYS:
        value = settings.config.get(key)
        if value and value not in output_paths:
            output_paths.append(value)

    for output_path in output_paths:
        path = Path(output_path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as file:
                file.write(marker)
        except OSError:
            logger.exception("Could not write processing marker to %s", path)

    log_file = settings.config.get("log_file")
    return Path(log_file) if log_file else None


def log_document_step(log_path: Path | None, message: str) -> None:
    """Append one worker step to the configured process log."""
    if log_path is None:
        return

    try:
        with log_path.open("a", encoding="utf-8") as file:
            file.write(f"{datetime.now(timezone.utc).isoformat()} | {message}\n")
    except OSError:
        logger.exception("Could not write document-processing log to %s", log_path)


@celery_app.task(name="documents.process_sample")
def process_document_sample(document_id: str, processing_run_id: str) -> dict[str, str]:
    """Confirm that a document job can be consumed from the Redis queue."""
    logger.info(
        "Received document-processing job: document_id=%s, processing_run_id=%s",
        document_id,
        processing_run_id,
    )
    return {
        "document_id": document_id,
        "processing_run_id": processing_run_id,
        "status": "accepted_by_worker",
    }


@celery_app.task(name="documents.process")
def process_document(document_id: int, processing_run_id: str) -> dict[str, str | int]:
    """Download, parse, chunk, and index one uploaded document."""
    run_id = UUID(processing_run_id)
    backend = MainBackendClient()
    log_path = mark_new_document_process(document_id, processing_run_id)

    try:
        log_document_step(log_path, "Starting document processing.")
        backend.update_status(document_id, run_id, "parsing", 5, "Downloading PDF.")

        with tempfile.TemporaryDirectory(prefix=f"rag-document-{document_id}-") as temp_dir:
            file_path = Path(temp_dir) / f"document_{document_id}.pdf"
            log_document_step(log_path, "Downloading PDF.")
            backend.download_document(document_id, file_path)

            backend.update_status(document_id, run_id, "parsing", 20, "Parsing PDF content.")
            from src.PIPELINE._2_parse.parser import run_parser

            log_document_step(log_path, "Parsing PDF content.")
            run_parser(str(file_path))

            backend.update_status(document_id, run_id, "chunking", 55, "Creating document chunks.")
            from src.PIPELINE._3_chunk.strategies.HSF.HSF_chunking import HSF_chunk

            log_document_step(log_path, "Creating document chunks.")

            def before_index() -> None:
                log_document_step(log_path, "Indexing searchable chunks.")
                backend.update_status(
                    document_id,
                    run_id,
                    "indexing",
                    80,
                    "Indexing searchable chunks.",
                )

            chunk_count = HSF_chunk(
                file_path=str(file_path),
                document_id=str(document_id),
                on_before_index=before_index,
            )

        backend.update_status(document_id, run_id, "ready", 100, "Document is ready for chat.")
        log_document_step(log_path, f"Document processing completed. chunk_count={chunk_count}")
        return {
            "document_id": document_id,
            "processing_run_id": processing_run_id,
            "chunk_count": chunk_count,
            "status": "ready",
        }
    except Exception:
        log_document_step(log_path, "Document processing failed; see worker exception log.")
        logger.exception("Document processing failed for document_id=%s", document_id)
        try:
            backend.update_status(
                document_id,
                run_id,
                "failed",
                0,
                "The document could not be processed.",
            )
        except Exception:
            logger.exception("Could not report failed status for document_id=%s", document_id)
        raise
