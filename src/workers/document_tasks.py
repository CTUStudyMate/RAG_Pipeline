"""Celery tasks for document ingestion."""

import logging
import tempfile
from pathlib import Path
from uuid import UUID

from src.clients.main_backend_client import MainBackendClient
from src.workers.celery_app import celery_app


logger = logging.getLogger(__name__)


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

    try:
        backend.update_status(document_id, run_id, "parsing", 5, "Downloading PDF.")

        with tempfile.TemporaryDirectory(prefix=f"rag-document-{document_id}-") as temp_dir:
            file_path = Path(temp_dir) / f"document_{document_id}.pdf"
            backend.download_document(document_id, file_path)

            backend.update_status(document_id, run_id, "parsing", 20, "Parsing PDF content.")
            from src.PIPELINE._2_parse.parser import run_parser

            run_parser(str(file_path))

            backend.update_status(document_id, run_id, "chunking", 55, "Creating document chunks.")
            from src.PIPELINE._3_chunk.strategies.HSF.HSF_chunking import HSF_chunk

            chunk_count = HSF_chunk(
                file_path=str(file_path),
                document_id=str(document_id),
                on_before_index=lambda: backend.update_status(
                    document_id,
                    run_id,
                    "indexing",
                    80,
                    "Indexing searchable chunks.",
                ),
            )

        backend.update_status(document_id, run_id, "ready", 100, "Document is ready for chat.")
        return {
            "document_id": document_id,
            "processing_run_id": processing_run_id,
            "chunk_count": chunk_count,
            "status": "ready",
        }
    except Exception:
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
