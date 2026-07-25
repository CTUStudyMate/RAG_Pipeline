"""Celery configuration for document-processing workers."""

import os
from pathlib import Path

from celery import Celery
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")
REDIS_URL = os.getenv("REDIS_URL")

if not REDIS_URL:
    raise RuntimeError("REDIS_URL must be configured before starting a Celery worker.")


celery_app = Celery(
    "rag_document_worker",
    broker=REDIS_URL,
    include=["src.workers.document_tasks"],
)

celery_app.conf.update(
    task_default_queue="document_processing",
    task_serializer="json",
    accept_content=["json"],
    result_backend=None,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    task_time_limit=3600,
    task_soft_time_limit=3300,
)
