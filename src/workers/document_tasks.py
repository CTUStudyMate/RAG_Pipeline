"""Celery tasks for document ingestion.

The sample task verifies the queue and worker setup. The real parse, chunk,
and storage pipeline will replace its body in a later step.
"""

import logging

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
